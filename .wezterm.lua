local wezterm = require("wezterm")

return {
	hide_tab_bar_if_only_one_tab = true,

	window_padding = {
		left = 0,
		right = 0,
		top = 0,
		bottom = 0,
	},

	window_background_opacity = 0.8,

	-- Mouse selection only fills the primary selection (middle-click paste),
	-- not the clipboard. Copy to the clipboard explicitly with Ctrl+Shift+C.
	mouse_bindings = {
		{
			event = { Up = { streak = 1, button = "Left" } },
			mods = "NONE",
			action = wezterm.action.CompleteSelectionOrOpenLinkAtMouseCursor("PrimarySelection"),
		},
		{
			event = { Up = { streak = 1, button = "Left" } },
			mods = "SHIFT",
			action = wezterm.action.CompleteSelectionOrOpenLinkAtMouseCursor("PrimarySelection"),
		},
		{
			event = { Up = { streak = 2, button = "Left" } },
			mods = "NONE",
			action = wezterm.action.CompleteSelection("PrimarySelection"),
		},
		{
			event = { Up = { streak = 3, button = "Left" } },
			mods = "NONE",
			action = wezterm.action.CompleteSelection("PrimarySelection"),
		},
	},
}
