# Auto-start tmux in local terminal, but not in VSCode
if [ -z "$TMUX" ] && [ "$TERM_PROGRAM" != "vscode" ]; then
  tmux attach || tmux new
fi

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

# Command to discover bluetooth cards: pactl list cards | grep -A20 bluez_card
# "hm" = headset mic: switch to HSP/HFP mode (lower audio quality, but enables mic), and set headset mic as default input
#alias hm='pactl set-card-profile bluez_card.78_2B_64_CE_B8_A6 headset-head-unit-msbc && pactl set-default-source bluez_input.78_2B_64_CE_B8_A6.0 && echo "Switched to headset mic (HSP/HFP mode)"'
# "ha" = headset audio: switch to A2DP mode (high audio quality, but mic disabled), and set headset as default output
#alias ha='pactl set-card-profile bluez_card.78_2B_64_CE_B8_A6 a2dp-sink && echo "Switched to headset audio (A2DP mode)"'

# Bluetooth headset card IDs
CARD1="bluez_card.78_2B_64_CE_B8_A6"   # Bose 700
CARD2="bluez_card.80_95_3A_F3_23_BC"   # Airpods 2 Pro
SRC1="bluez_input.78_2B_64_CE_B8_A6.0" # Bose 700
SRC2="bluez_input.80_95_3A_F3_23_BC.0" # Airpods 2 Pro

# "hm" = headset mic: switch to HSP/HFP mode (lower audio quality, but enables mic), and set headset mic as default input
alias hm='
  pactl set-card-profile "$CARD1" headset-head-unit-msbc || true;
  pactl set-card-profile "$CARD2" headset-head-unit-msbc || true;
  pactl set-default-source "$SRC1" || pactl set-default-source "$SRC2" || true;
  echo "Switched to headset mic (HSP/HFP mode)"
'

# "ha" = headset audio: switch to A2DP mode (high audio quality, but mic disabled), and set headset as default output
alias ha='
  pactl set-card-profile "$CARD1" a2dp-sink || true;
  pactl set-card-profile "$CARD2" a2dp-sink || true;
  echo "Switched to headset audio (A2DP mode)"
'

# Customize default PS1 (shell prompt)
parse_git_branch() {
  git rev-parse --is-inside-work-tree &>/dev/null || return
  branch=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null)
  maxlen=30
  ellipsis="..."
  if [[ ${#branch} -gt $maxlen ]]; then
    cutlen=$(( maxlen - ${#ellipsis} ))
    echo "${branch:0:$cutlen}${ellipsis}"
  else
    echo "$branch"
  fi
}
PS1='\[\e[1;34m\]\w\[\e[0m\]$(branch=$(parse_git_branch); [[ -n "$branch" ]] && echo " \[\e[1;33m\][$branch]\[\e[0m\]")\$ '
