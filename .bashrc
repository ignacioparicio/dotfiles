alias vim='nvim'

alias dv="cd /home/ignacio/.local/share/docker/volumes"

# control text-scaling-factor for  monitor hot-plugging, memo: z(zoom), zi (zoom in), zo (zoom out)
alias z='echo "text-scaling-factor: $(gsettings get org.gnome.desktop.interface text-scaling-factor)"'
alias zi='new_value=$(echo "$(gsettings get org.gnome.desktop.interface text-scaling-factor) + 0.25" | bc); gsettings set org.gnome.desktop.interface text-scaling-factor $new_value; echo "text-scaling-factor: $new_value"'
alias zo='new_value=$(echo "$(gsettings get org.gnome.desktop.interface text-scaling-factor) - 0.25" | bc); gsettings set org.gnome.desktop.interface text-scaling-factor $new_value; echo "text-scaling-factor: $new_value"'

alias load-venv="source ~/.venv/bin/activate"
load-venv