# TinyHugeBot Android packaging adaptation

The MIT-licensed Tiny Chess Bot Challenge submission contains a compressed managed DLL. Android Mono aborts when loading its stripped metadata because the GUID heap is absent. This directory keeps the submission payload and packages it as an ordinary assembly reference instead of executing its runtime decoder and AssemblyResolve hook.

`extract.py` decodes the decimal payload, verifies SHA-256 `2269e8215864e794a7f53826ef7eeed687a9a4163c0ca53dc8f86c84f26aa757`, and restores a GUID stream for the metadata reader. `Program.cs`, using build-only Mono.Cecil 0.11.6, writes a normal assembly, gives anonymous private members valid names, fixes the stripped System.Runtime reference, points the API reference at BoardLens.Android, exposes the bot constructor, and bounds both hash arrays and matching modulo operands from 25,165,824 to 262,144 entries. Search and evaluation instructions are preserved. Smaller tables can change playing strength.

Reproduce from this folder, using Python 3 and .NET 10:

```sh
python3 extract.py /tmp/tinyhuge-readable.dll
dotnet run --project Prepare.csproj -- /tmp/tinyhuge-readable.dll BoardLens.TinyHuge.dll
```

The resulting DLL is committed so app builds need no runtime decoding or build-time tool download. `Prepare.csproj` and Mono.Cecil are not app dependencies. The Challenge MIT notice is in ../../LICENSE-Chess-Challenge.txt. Original authors: Popax21 and atpx8. Source repository and submission commit are recorded in ../../sources.json.
