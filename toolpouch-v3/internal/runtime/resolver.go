package runtime

import (
	"fmt"
	"os/exec"
	"path/filepath"
	"strings"
)

// Resolver determines how to execute a script based on its extension
type Resolver struct{}

// NewResolver creates a new runtime resolver
func NewResolver() *Resolver {
	return &Resolver{}
}

// Resolve returns the command and args needed to run a script
// It looks for system-installed interpreters first
func (r *Resolver) Resolve(scriptPath string, runtimeOverride string) (string, []string, error) {
	ext := strings.ToLower(filepath.Ext(scriptPath))

	// Check for explicit runtime override
	if runtimeOverride != "" {
		return r.resolveByRuntime(runtimeOverride, scriptPath)
	}

	// Resolve by file extension
	switch ext {
	case ".py":
		return r.resolvePython(scriptPath)
	case ".ps1":
		return r.resolvePowerShell(scriptPath)
	case ".bat", ".cmd":
		return r.resolveBatch(scriptPath)
	case ".js":
		return r.resolveNode(scriptPath)
	default:
		return "", nil, fmt.Errorf("unsupported script extension: %s", ext)
	}
}

func (r *Resolver) resolveByRuntime(runtime string, scriptPath string) (string, []string, error) {
	switch strings.ToLower(runtime) {
	case "python":
		return r.resolvePython(scriptPath)
	case "pwsh", "powershell":
		return r.resolvePowerShell(scriptPath)
	case "cmd":
		return r.resolveBatch(scriptPath)
	case "node":
		return r.resolveNode(scriptPath)
	default:
		return "", nil, fmt.Errorf("unknown runtime override: %s", runtime)
	}
}

func (r *Resolver) resolvePython(scriptPath string) (string, []string, error) {
	// Try 'py' launcher first (Windows Python Launcher)
	if cmd, err := exec.LookPath("py"); err == nil {
		return cmd, []string{scriptPath}, nil
	}

	// Fall back to 'python'
	if cmd, err := exec.LookPath("python"); err == nil {
		return cmd, []string{scriptPath}, nil
	}

	// Try 'python3'
	if cmd, err := exec.LookPath("python3"); err == nil {
		return cmd, []string{scriptPath}, nil
	}

	return "", nil, fmt.Errorf("Python interpreter not found. Please install Python from python.org")
}

func (r *Resolver) resolvePowerShell(scriptPath string) (string, []string, error) {
	// Prefer PowerShell 7+ (pwsh)
	if cmd, err := exec.LookPath("pwsh"); err == nil {
		return cmd, []string{"-File", scriptPath}, nil
	}

	// Fall back to Windows PowerShell
	if cmd, err := exec.LookPath("powershell.exe"); err == nil {
		return cmd, []string{"-File", scriptPath}, nil
	}

	return "", nil, fmt.Errorf("PowerShell not found. Please install PowerShell")
}

func (r *Resolver) resolveBatch(scriptPath string) (string, []string, error) {
	// Use cmd.exe /c to run batch files
	if cmd, err := exec.LookPath("cmd.exe"); err == nil {
		return cmd, []string{"/c", scriptPath}, nil
	}

	// On non-Windows systems, this won't work, but we're Windows-only
	return "", nil, fmt.Errorf("cmd.exe not found")
}

func (r *Resolver) resolveNode(scriptPath string) (string, []string, error) {
	if cmd, err := exec.LookPath("node"); err == nil {
		return cmd, []string{scriptPath}, nil
	}

	return "", nil, fmt.Errorf("Node.js not found. Please install Node.js from nodejs.org")
}

// GetEmbeddedPythonPath returns the path to embedded Python if it exists
func (r *Resolver) GetEmbeddedPythonPath(embedDir string) string {
	candidates := []string{
		filepath.Join(embedDir, "python.exe"),
		filepath.Join(embedDir, "python", "python.exe"),
	}

	for _, candidate := range candidates {
		if _, err := exec.LookPath(candidate); err == nil {
			return candidate
		}
	}

	return ""
}
