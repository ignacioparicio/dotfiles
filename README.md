## About

This repo contains dotfiles to configure tmux and Neovim.

## Requirements

- `sudo apt install tmux neovim build-essentials fzf python3.12-venv ripgrep` (consider if a different Python version is needed)
- Install [Node](https://nodejs.org/en/download/package-manager)

## Usage

1. Consider wiping existing configuration:

   ```
   rm -rf ~/.local/share/nvim
   rm -rf ~/.cache/nvim
   rm -rf ~/.config/nvim
   ```

2. Install Packer, if not already installed:

   ```
   git clone --depth 1 https://github.com/wbthomason/packer.nvim \
   ~/.local/share/nvim/site/pack/packer/start/packer.nvim
   ```

3. Copy `lua/` and `init.lua`:

   ```
   mkdir -p ~/.config/nvim
   cp -r lua/ ~/.config/nvim/
   cp init.lua ~/.config/nvim/
   ```

4. Navigate to `lua/ignacio/packer.lua` in Neovim.
5. Source the file: `:so`.
6. Run `:PackerSync`.
7. Copy `after/`:

   ```
   cp -r after/ ~/.config/nvim/
   ```
