{
  lib,
  buildLinux,
  fetchFromGitHub,
}:

buildLinux (finalAttrs: {
  pname = "linux_ogc";
  version = "7.3.1-ogc6";
  modDirVersion = finalAttrs.version;

  src = fetchFromGitHub {
    owner = "OpenGamingCollective";
    repo = "linux";
    tag = "v${finalAttrs.version}";
    hash = "";
  };

  defconfig = "defconfig";
})
