vim.g.mapleader = " "
vim.keymap.set("n", "<leader>pv", vim.cmd.Ex)

-- Allow to move selection around, with auto-indenting
vim.keymap.set("v", "J", ":m '>+1<CR>gv=gv")
vim.keymap.set("v", "K", ":m '<-2<CR>gv=gv")

-- Don't move cursor on J
vim.keymap.set("n", "J", "mzJ`z")

-- Don't move cursor when navigating half a view
vim.keymap.set("n", "<C-d>", "<C-d>zz")
vim.keymap.set("n", "<C-u>", "<C-u>zz")

-- Keep cursors in the middle during search
vim.keymap.set("n", "n", "nzzzv")
vim.keymap.set("n", "N", "Nzzzv")

-- Allow <leader>p to keep copy buffer when pasting
vim.keymap.set("x", "<leader>p", [["_dP]])

-- Use <leader>y to yank to system clipboard
-- vim.keymap.set({"n", "v"}, "<leader>y", [["+y]])
-- vim.keymap.set("n", "<leader>Y", [["+Y]])

-- Delete to void register in both visual and normal mode
vim.keymap.set({"n", "v"}, "<leader>d", [["_d]])

-- Ensure ctrl+C fully replicates Esc
vim.keymap.set("i", "<C-c>", "<Esc>")

-- Get rid of Ex mode
vim.keymap.set("n", "Q", "<nop>")

-- ctrl+f to launch new tmux window
vim.keymap.set("n", "<C-f>", "<cmd>silent !tmux neww ~/.local/bin/scripts/tmux-sessionizer<CR>")

-- Format code on <leader>f
vim.keymap.set("n", "<leader>f", vim.lsp.buf.format)

-- Quickfix navigation
-- vim.keymap.set("n", "<C-k>", "<cmd>cnext<CR>zz")
-- vim.keymap.set("n", "<C-j>", "<cmd>cprev<CR>zz")
-- vim.keymap.set("n", "<leader>k", "<cmd>lnext<CR>zz")
-- vim.keymap.set("n", "<leader>j", "<cmd>lprev<CR>zz")

-- <leader>s gives a prompt to replace word the cursor is on
vim.keymap.set("n", "<leader>s", [[:%s/\<<C-r><C-w>\>/<C-r><C-w>/gI<Left><Left><Left>]])

-- <leader>x to make the current file executable
-- vim.keymap.set("n", "<leader>x", "<cmd>!chmod +x %<CR>", { silent = true })
