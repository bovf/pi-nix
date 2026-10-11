{
  lib,
  stdenvNoCC,
  python3,
  makeWrapper,
  ffmpeg,
  whisper-cpp,
  bubblewrap,
  bash,
  coreutils,
  fetchurl,
  writeText,
}: let
  python = python3.withPackages (p: [p.mcp p.numpy p.pydantic]);
  whisper = whisper-cpp.override {
    cudaSupport = false;
    rocmSupport = false;
    vulkanSupport = false;
  };
  model = fetchurl {
    name = "ggml-tiny.en.bin";
    url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-tiny.en.bin";
    hash = "sha256-kh5M+Ghv3Zk9zQgaXaW2w2W/3hFi5ysI11rHUomSCx8=";
  };
  modelCard = fetchurl {
    name = "whisper-model-card.md";
    url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/README.md";
    hash = "sha256-If2WcJiATzP8hOgD+w5at2ZtcYAfQCfPKKZeevCcF1g=";
  };
  defaults = writeText "badwater-video-defaults.json" (builtins.toJSON {
    ffmpeg = lib.getExe' ffmpeg "ffmpeg";
    ffprobe = lib.getExe' ffmpeg "ffprobe";
    whisper = lib.getExe' whisper "whisper-cli";
    bubblewrap = lib.getExe bubblewrap;
    bash = lib.getExe bash;
    timeout = lib.getExe' coreutils "timeout";
    toolPath = lib.makeBinPath [ffmpeg bash coreutils];
    inherit model;
    modelHash = "921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f";
    pipelineHash = builtins.hashString "sha256" (builtins.readFile ./engine.py + builtins.readFile ./store.py + builtins.readFile ./native.py);
    concurrency = 1;
    timeoutSeconds = 1200;
    maxAutomaticRepairAttempts = 2;
  });
in
  stdenvNoCC.mkDerivation {
    pname = "badwater-video";
    version = "0.1.0";
    src = ./.;
    dontUnpack = true;
    dontBuild = true;
    nativeBuildInputs = [makeWrapper];
    installPhase = ''
      runHook preInstall
      mkdir -p "$out/lib/badwater-video" "$out/bin" "$out/share/doc/badwater-video"
      for file in engine.py jobs.py main.py native.py store.py; do
        install -m644 "$src/$file" "$out/lib/badwater-video/$file"
      done
      cp -r "$src/skills" "$out/skills"
      install -m644 "$src/package.json" "$out/package.json"
      cp ${modelCard} "$out/share/doc/badwater-video/WHISPER-MODEL-CARD.md"
      makeWrapper ${python}/bin/python3 "$out/bin/badwater-video" \
        --add-flags "$out/lib/badwater-video/main.py" \
        --set BADWATER_VIDEO_DEFAULTS ${defaults} \
        --set BADWATER_VIDEO_ENGINE "$out/bin/badwater-video" \
        --set PYTHONDONTWRITEBYTECODE 1
      runHook postInstall
    '';
    doInstallCheck = true;
    installCheckPhase = ''
      runHook preInstallCheck
      export HOME="$TMPDIR/home" PYTHONPYCACHEPREFIX="$TMPDIR/bytecode"
      mkdir -p "$HOME"
      ${python}/bin/python3 -m compileall -q "$out/lib/badwater-video"
      "$out/bin/badwater-video" --help >/dev/null
      PYTHONPATH="$out/lib/badwater-video" ${python}/bin/python3 ${../../tests/video-unit.py}
      runHook postInstallCheck
    '';
    passthru = {inherit model modelCard defaults whisper python;};
    meta = {
      description = "Local indexed Pi video workflow with native Craft backends, CLI and lazy stdio MCP";
      mainProgram = "badwater-video";
      license = lib.licenses.mit;
      platforms = lib.platforms.linux;
    };
  }
