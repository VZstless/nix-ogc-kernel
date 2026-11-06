{
  lib,
  buildLinux,
  fetchFromGitHub,
}:

buildLinux rec {
  pname = "linux-ogc";
  version = "7.3.1-ogc6";
  modDirVersion = "7.3.1";

  src = fetchFromGitHub {
    owner = "OpenGamingCollective";
    repo = "linux";
    tag = "v${version}";
    hash = "sha256-ajhQv+mzKY99kkRGR5ucwK8R/WWf5PYPT93EgBKjgIg=";
  };

  defconfig = "defconfig";
}
