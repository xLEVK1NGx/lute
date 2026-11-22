# L.U.T.E
**L**EVK1NG's **U**nified **T**heme **E**ditor is a unified tool to change the themes of all your desktop apps. Each theme is a single JSONC file, that defines behaviours for all your favorite desktop apps. And if it doesn't support YOUR fav app, you can contribute by adding support for it!  
#### Currently supported apps (a.k.a. plugins):  
- [Kitty terminal emulator](https://sw.kovidgoyal.net/kitty/) [^1]
- [Hyprland wayland compositor](https://hypr.land) [^1]
- [Quickshell toolkit](https://quickshell.org) [^1]

#### Potential future plugins (they might or might not get implementations one day...):  
- Vivaldi browser
- Other browsers
- Other terminals (foot, alacritty, ghostty, GNOME terminal, Konsole)
- Other WMs
- VSCode
- TTYs
- Spicetify somehow

#### What will NOT be supported:  
- Windows-only apps.

## Installation
Run this command in your shell: `pipx install "git+https://github.com/xLEVK1NGx/lute.git"`  
It installs lute with all its dependencies, should work on any distro. 

## Contributing
Open Issues to discuss whether your feature may or may not be added, and if yes, you can start coding your plugin. Please only write plugins. The core lute behaviour is managed by me, and any core-changing pull requests will not be accepted.  



[^1]: keep in mind that this software is an early alpha so an app being "supported" means that it MOSTLY works.
