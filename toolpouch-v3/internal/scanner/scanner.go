package scanner

import (
	"os"
	"path/filepath"

	"github.com/gegestrnad/toolpouch-v3/internal/manifest"
)

// ToolInfo contains a tool's manifest and folder path
type ToolInfo struct {
	Manifest   *manifest.Manifest
	FolderPath string
	ScriptPath string
	Error      string // populated if there was an error loading the tool
}

// Scanner walks a tools directory and loads all valid tool manifests
type Scanner struct {
	toolsDir string
}

// New creates a new Scanner for the given tools directory
func New(toolsDir string) *Scanner {
	return &Scanner{
		toolsDir: toolsDir,
	}
}

// Scan walks the tools directory and returns all discovered tools
func (s *Scanner) Scan() ([]ToolInfo, error) {
	var tools []ToolInfo

	if _, err := os.Stat(s.toolsDir); os.IsNotExist(err) {
		return tools, nil // return empty list if tools dir doesn't exist
	}

	entries, err := os.ReadDir(s.toolsDir)
	if err != nil {
		return nil, err
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		folderPath := filepath.Join(s.toolsDir, entry.Name())
		manifestPath := filepath.Join(folderPath, "tool.toml")

		// Skip folders without tool.toml
		if _, err := os.Stat(manifestPath); os.IsNotExist(err) {
			continue
		}

		m, err := manifest.LoadFromFile(manifestPath)
		if err != nil {
			// Log warning but continue scanning other tools
			tools = append(tools, ToolInfo{
				FolderPath: folderPath,
				Error:      err.Error(),
			})
			continue
		}

		if err := m.Validate(); err != nil {
			tools = append(tools, ToolInfo{
				FolderPath: folderPath,
				Error:      err.Error(),
			})
			continue
		}

		tools = append(tools, ToolInfo{
			Manifest:   m,
			FolderPath: folderPath,
			ScriptPath: m.GetScriptPath(folderPath),
		})
	}

	return tools, nil
}
