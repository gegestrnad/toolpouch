package manifest

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestLoadFromFile(t *testing.T) {
	// Create a temporary test manifest
	tmpDir := t.TempDir()
	manifestContent := `
[tool]
name = "Test Tool"
description = "A test tool"
icon = "ti-tool"
script = "test.py"
long_running = false

[[params]]
id = "input_dir"
label = "Input folder"
type = "folder"
required = true

[[dependencies]]
import = "fitz"
package = "PyMuPDF"
version = ">=1.24"
ecosystem = "python"
`
	manifestPath := filepath.Join(tmpDir, "tool.toml")
	if err := os.WriteFile(manifestPath, []byte(manifestContent), 0644); err != nil {
		t.Fatalf("failed to write test manifest: %v", err)
	}

	m, err := LoadFromFile(manifestPath)
	if err != nil {
		t.Fatalf("LoadFromFile failed: %v", err)
	}

	if m.Tool.Name != "Test Tool" {
		t.Errorf("expected name 'Test Tool', got '%s'", m.Tool.Name)
	}
	if m.Tool.Script != "test.py" {
		t.Errorf("expected script 'test.py', got '%s'", m.Tool.Script)
	}
	if len(m.Tool.Params) != 1 {
		t.Errorf("expected 1 param, got %d", len(m.Tool.Params))
	}
	if len(m.Tool.Dependencies) != 1 {
		t.Errorf("expected 1 dependency, got %d", len(m.Tool.Dependencies))
	}
	if m.Tool.Dependencies[0].ImportName != "fitz" {
		t.Errorf("expected import 'fitz', got '%s'", m.Tool.Dependencies[0].ImportName)
	}
	if m.Tool.Dependencies[0].Ecosystem != "python" {
		t.Errorf("expected ecosystem 'python', got '%s'", m.Tool.Dependencies[0].Ecosystem)
	}
}

func TestLoadFromFile_BackwardCompat(t *testing.T) {
	// Test manifest without explicit ecosystem (should default to "python")
	tmpDir := t.TempDir()
	manifestContent := `
[tool]
name = "Legacy Tool"
description = "A legacy tool"
script = "legacy.py"

[[dependencies]]
import = "requests"
package = "requests"
version = ">=2.0"
`
	manifestPath := filepath.Join(tmpDir, "tool.toml")
	if err := os.WriteFile(manifestPath, []byte(manifestContent), 0644); err != nil {
		t.Fatalf("failed to write test manifest: %v", err)
	}

	m, err := LoadFromFile(manifestPath)
	if err != nil {
		t.Fatalf("LoadFromFile failed: %v", err)
	}

	if len(m.Tool.Dependencies) != 1 {
		t.Fatalf("expected 1 dependency, got %d", len(m.Tool.Dependencies))
	}
	if m.Tool.Dependencies[0].Ecosystem != "python" {
		t.Errorf("expected default ecosystem 'python', got '%s'", m.Tool.Dependencies[0].Ecosystem)
	}
}

func TestValidate(t *testing.T) {
	tests := []struct {
		name    string
		content string
		wantErr bool
	}{
		{
			name: "valid manifest",
			content: `
[tool]
name = "Valid"
script = "test.py"
`,
			wantErr: false,
		},
		{
			name: "missing name",
			content: `
[tool]
script = "test.py"
`,
			wantErr: true,
		},
		{
			name: "missing script",
			content: `
[tool]
name = "Valid"
`,
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tmpDir := t.TempDir()
			manifestPath := filepath.Join(tmpDir, "tool.toml")
			if err := os.WriteFile(manifestPath, []byte(tt.content), 0644); err != nil {
				t.Fatalf("failed to write test manifest: %v", err)
			}

			m, err := LoadFromFile(manifestPath)
			if err != nil && !tt.wantErr {
				t.Fatalf("LoadFromFile failed unexpectedly: %v", err)
			}

			if m != nil {
				err = m.Validate()
				if (err != nil) != tt.wantErr {
					t.Errorf("Validate() error = %v, wantErr %v", err, tt.wantErr)
				}
			}
		})
	}
}

func TestGetScriptPath(t *testing.T) {
	tmpDir := t.TempDir()
	manifestContent := `
[tool]
name = "Test"
script = "myscript.py"
`
	manifestPath := filepath.Join(tmpDir, "tool.toml")
	os.WriteFile(manifestPath, []byte(manifestContent), 0644)

	m, _ := LoadFromFile(manifestPath)
	scriptPath := m.GetScriptPath(tmpDir)

	expected := filepath.Join(tmpDir, "myscript.py")
	if scriptPath != expected {
		t.Errorf("expected '%s', got '%s'", expected, scriptPath)
	}
}

func TestMalformedTOML(t *testing.T) {
	tmpDir := t.TempDir()
	manifestPath := filepath.Join(tmpDir, "tool.toml")
	invalidContent := `[tool
name = "broken
`
	if err := os.WriteFile(manifestPath, []byte(invalidContent), 0644); err != nil {
		t.Fatalf("failed to write test manifest: %v", err)
	}

	_, err := LoadFromFile(manifestPath)
	if err == nil {
		t.Error("expected error for malformed TOML, got nil")
	}
	if !strings.Contains(err.Error(), "failed to parse TOML") {
		t.Errorf("expected parse error, got: %v", err)
	}
}
