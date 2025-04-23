alias vim='nvim'
# alias vim='NVIM_APPNAME="nvim-kickstart" nvim' # alternative with multiple configs
# alias sudovim='sudo env NVIM_APPNAME="nvim-kickstart" nvim'


alias dv="cd /home/ignacio/.local/share/docker/volumes"

# control text-scaling-factor for monitor hot-plugging, memo: z(zoom), zi (zoom in), zo (zoom out)
alias z='echo "text-scaling-factor: $(gsettings get org.gnome.desktop.interface text-scaling-factor)"'
alias zi='new_value=$(echo "$(gsettings get org.gnome.desktop.interface text-scaling-factor) + 0.25" | bc); gsettings set org.gnome.desktop.interface text-scaling-factor $new_value; echo "text-scaling-factor: $new_value"'
alias zo='new_value=$(echo "$(gsettings get org.gnome.desktop.interface text-scaling-factor) - 0.25" | bc); gsettings set org.gnome.desktop.interface text-scaling-factor $new_value; echo "text-scaling-factor: $new_value"'

alias load-venv="source ~/.venv/bin/activate"
load-venv

alias psql-ctd='psql -h host -p 21699 -U pxl050 -d transactions'
alias psql-ctd-ctd='psql -h host -p 21699 -U ctd -d transactions' # Temporarily update password in .profile

# "hm" = headset mic: switch to HSP/HFP mode (lower audio quality, but enables mic), and set headset mic as default input
alias hm='pactl set-card-profile bluez_card.78_2B_64_CE_B8_A6 headset-head-unit-msbc && pactl set-default-source bluez_input.78_2B_64_CE_B8_A6.0'
# "ha" = headset audio: switch to A2DP mode (high audio quality, but mic disabled), and set headset as default output
alias ha='pactl set-card-profile bluez_card.78_2B_64_CE_B8_A6 a2dp-sink'
