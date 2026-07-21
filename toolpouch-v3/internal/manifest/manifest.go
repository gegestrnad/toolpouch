package manifest

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/BurntSushi/toml"
)

// ToolParam represents a single parameter definition from tool.toml
type ToolParam struct {
	ID          string   `toml:"id"`
	Label       string   `toml:"label"`
	Type        string   `toml:"type"` // text | folder | folders | file | files | save | dropdown
	Placeholder string   `toml:"placeholder"`
	Required    bool     `toml:"required"`
	Icon        string   `toml:"icon"`
	Filter      string   `toml:"filter"`
	Options     []string `toml:"options"`
	Default     string   `toml:"default"`
}

// ToolDependency represents a dependency declaration from tool.toml
type ToolDependency struct {
	ImportName string `toml:"import"`
	Package    string `toml:"package"`
	Version    string `toml:"version"`
	Ecosystem  string `toml:"ecosystem"` // python | node | powershell | none
	Notes      string `toml:"notes"`
}

// Tool represents a parsed tool.toml manifest
type Tool struct {
	Name         string           `toml:"name"`
	Description  string           `toml:"description"`
	Icon         string           `toml:"icon"`
	Script       string           `toml:"script"`
	LongRunning  bool             `toml:"long_running"`
	Runtime      string           `toml:"runtime"` // optional: python | pwsh | powershell | cmd | node
	Params       []ToolParam      `toml:"params,omitempty"`
	Dependencies []ToolDependency `toml:"dependencies,omitempty"`
}

// Manifest represents the full TOML structure
type Manifest struct {
	Tool         Tool             `toml:"tool"`
	Params       []ToolParam      `toml:"params,omitempty"`
	Dependencies []ToolDependency `toml:"dependencies,omitempty"`
}

// LoadFromFile reads and parses a tool.toml file
func LoadFromFile(path string) (*Manifest, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read manifest: %w", err)
	}

	var manifest Manifest
	if _, err := toml.Decode(string(data), &manifest); err != nil {
		return nil, fmt.Errorf("failed to parse TOML: %w", err)
	}

	// Merge top-level params and dependencies into tool struct for convenience
	if len(manifest.Params) > 0 && len(manifest.Tool.Params) == 0 {
		manifest.Tool.Params = manifest.Params
	}
	if len(manifest.Dependencies) > 0 && len(manifest.Tool.Dependencies) == 0 {
		manifest.Tool.Dependencies = manifest.Dependencies
	}

	// Set default ecosystem to "python" for backward compatibility
	for i := range manifest.Tool.Dependencies {
		if manifest.Tool.Dependencies[i].Ecosystem == "" {
			manifest.Tool.Dependencies[i].Ecosystem = "python"
		}
	}

	return &manifest, nil
}

// Validate checks if the manifest has required fields
func (m *Manifest) Validate() error {
	if m.Tool.Name == "" {
		return fmt.Errorf("tool name is required")
	}
	if m.Tool.Script == "" {
		return fmt.Errorf("tool script is required")
	}
	return nil
}

// GetScriptPath returns the full path to the script file
func (m *Manifest) GetScriptPath(folderPath string) string {
	return filepath.Join(folderPath, m.Tool.Script)
}
