package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
)

// Config represents the application configuration
type Config struct {
	mu sync.RWMutex

	Theme          string   `json:"theme"`
	WindowGeometry string   `json:"window.geometry,omitempty"`
	LastTool       string   `json:"last_tool,omitempty"`
	RecentTools    []string `json:"recent_tools"`
	FavoriteTools  []string `json:"favorite_tools"`
	SortOrder      string   `json:"tool_sort_order"`
}

// Manager handles loading and saving configuration
type Manager struct {
	configDir  string
	configFile string
	config     *Config
}

// NewManager creates a new configuration manager
func NewManager() (*Manager, error) {
	// Get APPDATA on Windows, or fall back to home directory
	appData := os.Getenv("APPDATA")
	if appData == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return nil, err
		}
		appData = home
	}

	configDir := filepath.Join(appData, "ToolPouch")
	if err := os.MkdirAll(configDir, 0755); err != nil {
		return nil, err
	}

	m := &Manager{
		configDir:  configDir,
		configFile: filepath.Join(configDir, "config.json"),
		config:     defaultConfig(),
	}

	if err := m.load(); err != nil {
		// If loading fails, use defaults (already set)
	}

	return m, nil
}

func defaultConfig() *Config {
	return &Config{
		Theme:       "Modern Dark",
		RecentTools: []string{},
		FavoriteTools: []string{},
		SortOrder:   "Default",
	}
}

func (m *Manager) load() error {
	data, err := os.ReadFile(m.configFile)
	if err != nil {
		if os.IsNotExist(err) {
			return nil // Use defaults
		}
		return err
	}

	var loaded Config
	if err := json.Unmarshal(data, &loaded); err != nil {
		return err
	}

	m.config = mergeConfigs(defaultConfig(), &loaded)
	return nil
}

func mergeConfigs(defaults, loaded *Config) *Config {
	result := *defaults

	if loaded.Theme != "" {
		result.Theme = loaded.Theme
	}
	if loaded.WindowGeometry != "" {
		result.WindowGeometry = loaded.WindowGeometry
	}
	if loaded.LastTool != "" {
		result.LastTool = loaded.LastTool
	}
	if len(loaded.RecentTools) > 0 {
		result.RecentTools = limitList(loaded.RecentTools, 10)
	}
	if len(loaded.FavoriteTools) > 0 {
		result.FavoriteTools = loaded.FavoriteTools
	}
	if loaded.SortOrder != "" {
		result.SortOrder = loaded.SortOrder
	}

	return &result
}

func limitList(list []string, limit int) []string {
	if len(list) <= limit {
		return list
	}
	return list[:limit]
}

// Save writes the current configuration to disk
func (m *Manager) Save() error {
	m.mu.RLock()
	defer m.mu.RUnlock()

	data, err := json.MarshalIndent(m.config, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(m.configFile, data, 0644)
}

// Get retrieves a configuration value
func (m *Manager) Get(key string) interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	switch key {
	case "theme":
		return m.config.Theme
	case "window.geometry":
		return m.config.WindowGeometry
	case "last_tool":
		return m.config.LastTool
	case "recent_tools":
		return m.config.RecentTools
	case "favorite_tools":
		return m.config.FavoriteTools
	case "tool_sort_order":
		return m.config.SortOrder
	default:
		return nil
	}
}

// Set updates a configuration value
func (m *Manager) Set(key string, value interface{}) {
	m.mu.Lock()
	defer m.mu.Unlock()

	switch key {
	case "theme":
		if s, ok := value.(string); ok {
			m.config.Theme = s
		}
	case "window.geometry":
		if s, ok := value.(string); ok {
			m.config.WindowGeometry = s
		}
	case "last_tool":
		if s, ok := value.(string); ok {
			m.config.LastTool = s
		}
	case "recent_tools":
		if list, ok := value.([]string); ok {
			m.config.RecentTools = limitList(list, 10)
		}
	case "favorite_tools":
		if list, ok := value.([]string); ok {
			m.config.FavoriteTools = list
		}
	case "tool_sort_order":
		if s, ok := value.(string); ok {
			m.config.SortOrder = s
		}
	}
}

// AddRecentTool adds a tool to the recent tools list
func (m *Manager) AddRecentTool(toolName string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	// Remove if already exists
	for i, t := range m.config.RecentTools {
		if t == toolName {
			m.config.RecentTools = append(m.config.RecentTools[:i], m.config.RecentTools[i+1:]...)
			break
		}
	}

	// Add to front
	m.config.RecentTools = append([]string{toolName}, m.config.RecentTools...)
	m.config.RecentTools = limitList(m.config.RecentTools, 10)
}

// IsFavorite checks if a tool is favorited
func (m *Manager) IsFavorite(toolName string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()

	for _, t := range m.config.FavoriteTools {
		if t == toolName {
			return true
		}
	}
	return false
}

// ToggleFavorite adds or removes a tool from favorites
func (m *Manager) ToggleFavorite(toolName string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	for i, t := range m.config.FavoriteTools {
		if t == toolName {
			// Remove
			m.config.FavoriteTools = append(m.config.FavoriteTools[:i], m.config.FavoriteTools[i+1:]...)
			return
		}
	}

	// Add to front
	m.config.FavoriteTools = append([]string{toolName}, m.config.FavoriteTools...)
}

// GetConfigDir returns the configuration directory path
func (m *Manager) GetConfigDir() string {
	return m.configDir
}
