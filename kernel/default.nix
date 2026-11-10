{
  callPackage,
  ...
}@args:
let
  variants = builtins.fromJSON (builtins.readFile ./versions.json);
  mkOgcKernel = callPackage ./mkOgcKernel.nix args;
in
  builtins.mapAttrs
    (pname: spec: mkOgcKernel (spec // { inherit pname; }))
    variants
