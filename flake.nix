{
  description = "CachyOS Kernels";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable-small";
    flake-parts.url = "github:hercules-ci/flake-parts";
    flake-compat = {
      url = "github:NixOS/flake-compat";
      flake = false;
    };
  };
  outputs = inputs@{ self, nixpkgs, flake-parts, ... }:

    let
      pkgs = import inputs.nixpkgs {
        inherit system;
      };
      kernel = pkgs.callPackage ./kernel { };
      system = "x86_64-linux";
    in {
      packages.${system} = {
        linux-ogc = kernel;
        kernelPackages = pkgs.linuxPackagesFor kernel;
        config = kernel.configfile;
      };
    };
}
