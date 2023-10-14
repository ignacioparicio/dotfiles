local builtin = require('telescope.builtin')
vim.keymap.set('n', '<leader>pf', builtin.find_files, {})
vim.keymap.set('n', '<C-p>', builtin.git_files, {})
vim.keymap.set('n', '<leader>ps', function()
    builtin.grep_string({ search = vim.fn.input("Grep > ") });
end)

local function is_image(filepath)
    local image_extensions = { 'png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff' }
    local split_path = vim.split(filepath:lower(), '.', { plain = true })
    local extension = split_path[#split_path]
    return vim.tbl_contains(image_extensions, extension)
end

_G.open_with_eog = function(filepath)
    print("Attempting to open: " .. filepath)
    os.execute('eog ' .. filepath .. ' &')
end

local actions = require("telescope.actions")
require('telescope').setup {
    defaults = {
        mappings = {
            i = {
                ["<CR>"] = function(prompt_bufnr)
                    local entry = require("telescope.actions.state").get_selected_entry()
                    local filepath = entry and entry.value or nil
                    if filepath and is_image(filepath) then
                        actions.close(prompt_bufnr)
                        _G.open_with_eog(filepath)
                    else
                        actions.select_default(prompt_bufnr)
                    end
                end
            },
        },
    },
}
