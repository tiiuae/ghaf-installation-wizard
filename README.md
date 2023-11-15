# ghaf-installation-wizard

Ghaf installation wizards help users of [Ghaf](https://github.com/tiiuae/ghaf)
to settle in which their own nix configuration of the system.

It’s mainly targeted at newcomers, but we have plans of extending it to automate
common tasks related to system redeployment.

## Build And Run

As this project mainly oriented to the users of Nix package manager, you shall
have it installed on your system in order to use installer. And also it is
required to have [flakes
enabled](https://nixos.wiki/wiki/Flakes#Enable_flakes_permanently_in_NixOS).

After this you can run wizard by simply typing following in your terminal:

``` sh
nix run github:tiiuae/ghaf-installation-wizard
```

This will run command will generate your own configuration and help you to deploy it for the first time!
