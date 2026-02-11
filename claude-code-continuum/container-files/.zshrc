# Claude Code Continuum - Container .zshrc
# Sanitized version for containerized environment

# Path to oh-my-zsh installation
export ZSH="/home/claude/.oh-my-zsh"

# Theme
ZSH_THEME="powerlevel10k/powerlevel10k"

# History settings
setopt inc_append_history
setopt share_history

# Plugins (removed macOS/brew specific)
plugins=(git colored-man-pages colorize pip python zsh-syntax-highlighting zsh-autosuggestions)

source $ZSH/oh-my-zsh.sh

# Editor
export EDITOR='vim'

# Useful aliases
alias du='dust'
alias find='fd'
alias h='history 1'
alias rgh='history 1 | rg'

# Git aliases
alias grr='git review --reviewers'
alias grm='git rebase master'
alias grum='git rebase upstream/master'
alias gfum='git fetch upstream && git merge upstream/master'

# Git functions
unalias gfa 2>/dev/null || true
gfa() {
  git fetch --all --prune
  for b in master release-4.21 release-4.20 release-4.19 release-4.18 release-4.17 release-4.16; do
    git checkout "$b" &&
    git reset --hard "upstream/$b" &&
    git push origin "$b"
  done
}

# Go environment
export GOPATH=$HOME/go
export PATH=$PATH:$GOPATH/bin
export PATH=$PATH:/usr/local/go/bin

# Tab completion
autoload -Uz compinit && compinit

# Paste optimization for zsh-autosuggestions
pasteinit() {
  OLD_SELF_INSERT=${${(s.:.)widgets[self-insert]}[2,3]}
  zle -N self-insert url-quote-magic
}

pastefinish() {
  zle -N self-insert $OLD_SELF_INSERT
}
zstyle :bracketed-paste-magic paste-init pasteinit
zstyle :bracketed-paste-magic paste-finish pastefinish
