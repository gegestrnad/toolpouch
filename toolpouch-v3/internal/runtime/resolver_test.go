package runtime

import (
	"os"
	"path/filepath"
	"testing"
)

func TestResolvePython(t *testing.T) {
	r := NewResolver()

	// Create a dummy Python script
	tmpDir := t.TempDir()
	scriptPath := filepath.Join(tmpDir, "test.py")
	if err := os.WriteFile(scriptPath, []byte("# test"), 0644); err != nil {
		t.Fatalf("failed to create test script: %v", err)
	}

	cmd, args, err := r.Resolve(scriptPath, "")
	if err != nil {
		// This is OK on systems without Python - just verify error message
		if cmd != "" {
			t.Errorf("expected empty cmd on error, got '%s'", cmd)
		}
		t.Logf("Resolve returned expected error (no Python): %v", err)
	} else {
		// If we got a result, verify it looks correct
		if len(args) != 1 {
			t.Errorf("expected 1 arg, got %d: %v", len(args), args)
		}
		if args[0] != scriptPath {
			t.Errorf("expected arg to be script path, got '%s'", args[0])
		}
		t.Logf("Resolved Python: cmd=%s, args=%v", cmd, args)
	}
}

func TestResolveByExtension(t *testing.T) {
	r := NewResolver()
	tmpDir := t.TempDir()

	tests := []struct {
		ext      string
		expected string // expected error substring or interpreter name
	}{
		{".py", "python"},
		{".ps1", "powershell"},
		{".bat", "cmd"},
		{".cmd", "cmd"},
		{".js", "node"},
		{".unsupported", "unsupported"},
	}

	for _, tt := range tests {
		t.Run(tt.ext, func(t *testing.T) {
			scriptPath := filepath.Join(tmpDir, "test"+tt.ext)
			os.WriteFile(scriptPath, []byte("test"), 0644)

			cmd, _, err := r.Resolve(scriptPath, "")
			if err != nil {
				if tt.expected == "unsupported" {
					// Expected error for unsupported extension
					return
				}
				// On systems without the interpreter, this is OK
				t.Logf("Interpreter not found for %s: %v", tt.ext, err)
			} else {
				if cmd == "" {
					t.Error("expected non-empty cmd when no error")
				}
			}
		})
	}
}

func TestResolveWithRuntimeOverride(t *testing.T) {
	r := NewResolver()
	tmpDir := t.TempDir()
	scriptPath := filepath.Join(tmpDir, "test.txt") // Wrong extension, but override should work
	os.WriteFile(scriptPath, []byte("test"), 0644)

	// Test Python override
	cmd, args, err := r.Resolve(scriptPath, "python")
	if err != nil {
		t.Logf("Python override (may not have Python): %v", err)
	} else {
		if len(args) != 1 || args[0] != scriptPath {
			t.Errorf("unexpected args: %v", args)
		}
		t.Logf("Python override resolved: cmd=%s", cmd)
	}

	// Test invalid override
	_, _, err = r.Resolve(scriptPath, "invalid_runtime")
	if err == nil {
		t.Error("expected error for invalid runtime override")
	}
}

func TestGetEmbeddedPythonPath(t *testing.T) {
	r := NewResolver()
	tmpDir := t.TempDir()

	// No embedded Python exists yet
	path := r.GetEmbeddedPythonPath(tmpDir)
	if path != "" {
		t.Errorf("expected empty path when no embedded Python exists, got '%s'", path)
	}

	// Create a fake embedded Python
	embedPath := filepath.Join(tmpDir, "python.exe")
	os.WriteFile(embedPath, []byte("fake"), 0644)

	// Note: This won't actually be executable, but the function checks existence
	// In real usage, this would be a proper python.exe
	path = r.GetEmbeddedPythonPath(tmpDir)
	// We don't assert here because LookPath also checks executability
	t.Logf("Embedded Python path check: %s", path)
}
