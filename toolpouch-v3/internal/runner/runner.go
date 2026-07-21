package runner

import (
	"bufio"
	"context"
	"io"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"sync"
)

// OutputLine represents a single line of output from a running tool
type OutputLine struct {
	Text  string `json:"text"`
	Level string `json:"level"` // info, ok, warn, error
}

// ProgressEvent represents a progress update
type ProgressEvent struct {
	Percentage int `json:"percentage"`
}

// RunResult represents the final result of a tool execution
type RunResult struct {
	Success   bool   `json:"success"`
	ExitCode  int    `json:"exitCode"`
	ErrorMsg  string `json:"errorMsg,omitempty"`
}

// Runner handles executing tools and streaming their output
type Runner struct {
	mu           sync.Mutex
	cmd          *exec.Cmd
	cancel       context.CancelFunc
	isRunning    bool
	onOutput     func(line OutputLine)
	onProgress   func(progress ProgressEvent)
	onComplete   func(result RunResult)
}

// NewRunner creates a new tool runner
func NewRunner() *Runner {
	return &Runner{}
}

// SetCallbacks sets the callback functions for output events
func (r *Runner) SetCallbacks(
	onOutput func(line OutputLine),
	onProgress func(progress ProgressEvent),
	onComplete func(result RunResult),
) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.onOutput = onOutput
	r.onProgress = onProgress
	r.onComplete = onComplete
}

// Run executes a command with the given arguments
func (r *Runner) Run(command string, args []string, env map[string]string) error {
	r.mu.Lock()
	if r.isRunning {
		r.mu.Unlock()
		return nil
	}
	r.isRunning = true
	r.mu.Unlock()

	ctx, cancel := context.WithCancel(context.Background())
	r.mu.Lock()
	r.cancel = cancel
	r.cmd = exec.CommandContext(ctx, command, args...)
	r.mu.Unlock()

	// Set environment variables
	if len(env) > 0 {
		r.cmd.Env = make([]string, 0, len(env))
		for k, v := range env {
			r.cmd.Env = append(r.cmd.Env, k+"="+v)
		}
	}

	// Get stdout pipe
	stdout, err := r.cmd.StdoutPipe()
	if err != nil {
		r.setNotRunning()
		if r.onComplete != nil {
			r.onComplete(RunResult{Success: false, ErrorMsg: err.Error()})
		}
		return err
	}

	// Start the command
	if err := r.cmd.Start(); err != nil {
		r.setNotRunning()
		if r.onComplete != nil {
			r.onComplete(RunResult{Success: false, ErrorMsg: err.Error()})
		}
		return err
	}

	// Stream output in a goroutine
	go r.streamOutput(stdout)

	// Wait for completion in a goroutine
	go r.waitForCompletion()

	return nil
}

func (r *Runner) streamOutput(stdout io.ReadCloser) {
	defer stdout.Close()

	scanner := bufio.NewScanner(stdout)
	progressRegex := regexp.MustCompile(`^PROGRESS:(\d+)$`)

	for scanner.Scan() {
		line := scanner.Text()
		outputLine := r.parseLine(line, progressRegex)
		
		r.mu.Lock()
		onOutput := r.onOutput
		r.mu.Unlock()

		if onOutput != nil && outputLine != nil {
			onOutput(*outputLine)
		}
	}
}

func (r *Runner) parseLine(line string, progressRegex *regexp.Regexp) *OutputLine {
	// Check for progress indicator
	if matches := progressRegex.FindStringSubmatch(line); matches != nil {
		if pct, err := strconv.Atoi(matches[1]); err == nil {
			r.mu.Lock()
			onProgress := r.onProgress
			r.mu.Unlock()
			
			if onProgress != nil {
				onProgress(ProgressEvent{Percentage: clamp(pct, 0, 100)})
			}
		}
		return nil // Progress lines don't produce output
	}

	// Determine log level
	level := "info"
	if strings.HasPrefix(line, "[OK]") {
		level = "ok"
	} else if strings.HasPrefix(line, "[WARN]") || strings.HasPrefix(line, "Warning") {
		level = "warn"
	} else if strings.HasPrefix(line, "[ERROR]") || strings.HasPrefix(line, "ERROR") || strings.HasPrefix(line, "Traceback") {
		level = "error"
	}

	return &OutputLine{
		Text:  line,
		Level: level,
	}
}

func (r *Runner) waitForCompletion() {
	err := r.cmd.Wait()
	
	r.setNotRunning()

	success := err == nil
	exitCode := 0
	errorMsg := ""

	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
			errorMsg = exitErr.Error()
		} else {
			errorMsg = err.Error()
		}
	}

	r.mu.Lock()
	onComplete := r.onComplete
	r.mu.Unlock()

	if onComplete != nil {
		onComplete(RunResult{
			Success:  success,
			ExitCode: exitCode,
			ErrorMsg: errorMsg,
		})
	}
}

// Stop terminates a running process
func (r *Runner) Stop() {
	r.mu.Lock()
	defer r.mu.Unlock()

	if !r.isRunning || r.cmd == nil {
		return
	}

	if r.cancel != nil {
		r.cancel()
	}

	// Kill the process
	if r.cmd.Process != nil {
		r.cmd.Process.Kill()
	}

	r.isRunning = false
}

// IsRunning returns whether a tool is currently executing
func (r *Runner) IsRunning() bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.isRunning
}

func (r *Runner) setNotRunning() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.isRunning = false
}

func clamp(value, min, max int) int {
	if value < min {
		return min
	}
	if value > max {
		return max
	}
	return value
}
