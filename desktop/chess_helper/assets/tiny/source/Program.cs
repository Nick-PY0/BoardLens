using System.Reflection;
using System.Runtime.Loader;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using ChessChallenge.API;
using CoreBoard=ChessChallenge.Chess.Board;
using CoreMove=ChessChallenge.Chess.MoveUtility;
using BotTimer=ChessChallenge.API.Timer;

class Program {
 static TextWriter Output=TextWriter.Null;
 static readonly object SendLock=new();
 static string position="startpos";
 static IChessBot? bot;
 static int generation;
 static void Send(string line){lock(SendLock){Output.WriteLine(line);Output.Flush();}}
 static void Main(string[] args){
  Output=Console.Out;
  if(args.Length!=2){Console.Error.WriteLine("Use source.cs bot-name");Environment.Exit(2);}
  try {
   var source=File.ReadAllText(args[0]).Replace("#define ELECTRIC_SHOCKWAVE_GAMBIT", "// GC attack disabled in isolated BoardLens adapter");
   var paths=((string)AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES")!).Split(Path.PathSeparator).Append(Assembly.GetExecutingAssembly().Location).Distinct();
   if(Path.GetFileName(args[0])=="Bot_303.cs")source=System.Text.RegularExpressions.Regex.Replace(source,@"(?<![\w.])(Abs|Max|Min)\(","Math.$1(");
   var refs=paths.Select(p=>MetadataReference.CreateFromFile(p));
   var compilation=CSharpCompilation.Create("SelectedBot",new[]{CSharpSyntaxTree.ParseText(source)},refs,new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary,optimizationLevel:OptimizationLevel.Release,allowUnsafe:true));
   using var memory=new MemoryStream();var emitted=compilation.Emit(memory);
   if(!emitted.Success)throw new Exception(string.Join("\n",emitted.Diagnostics.Where(d=>d.Severity==DiagnosticSeverity.Error)));
   memory.Position=0;var assembly=AssemblyLoadContext.Default.LoadFromStream(memory);
   var type=assembly.GetTypes().First(t=>typeof(IChessBot).IsAssignableFrom(t)&&!t.IsAbstract);
   // Original bots may print diagnostics; keep UCI output separate.
   Console.SetOut(Console.Error);bot=(IChessBot)Activator.CreateInstance(type)!;
   string? line;
   while((line=Console.ReadLine())!=null){
    if(line=="uci"){Send("id name Tiny Chess Bot - "+args[1]);Send("id author Original challenge authors / BoardLens UCI adapter");Send("uciok");}
    else if(line=="isready")Send("readyok");
    else if(line.StartsWith("position "))position=line[9..];
    else if(line=="ucinewgame")position="startpos";
    else if(line.StartsWith("go")){int tag=++generation;string requested=position;int budget=1000;var pieces=line.Split(' ');int at=Array.IndexOf(pieces,"movetime");if(at>=0&&at+1<pieces.Length)int.TryParse(pieces[at+1],out budget);budget=Math.Clamp(budget,100,300000);
     Task.Run(()=>Think(requested,budget,tag));
    }
    else if(line=="stop"||line=="quit")Environment.Exit(0);
   }
  }catch(Exception error){Console.Error.WriteLine(error);Environment.Exit(2);}
 }
 static void Think(string requested,int budget,int tag){
  try {
   var pieces=requested.Split(' ',StringSplitOptions.RemoveEmptyEntries);var board=new CoreBoard();
   int index=pieces[0]=="startpos"?1:7;
   board.LoadPosition(pieces[0]=="startpos"?"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1":string.Join(" ",pieces.Skip(1).Take(6)));
   if(index<pieces.Length&&pieces[index]=="moves")foreach(var move in pieces.Skip(index+1))board.MakeMove(CoreMove.GetMoveFromUCIName(move,board),false);
   var exposed=new ChessChallenge.API.Board(board);
   var timer=new BotTimer(budget*10,budget*10,budget*10,0);
   // A bot which ignores its clock cannot lock up the desktop.
   new Thread(()=>{Thread.Sleep(budget+200);if(tag==generation){Send("info string Requested thinking budget exceeded");Send("bestmove 0000");Environment.Exit(0);}}){IsBackground=true}.Start();
   var chosen=bot!.Think(exposed,timer);
   if(!new ChessChallenge.API.Board(board).GetLegalMoves().Any(m=>m.RawValue==chosen.RawValue))throw new Exception("Bot returned an illegal move");
   if(tag!=generation)return;
   ++generation;string uci=chosen.StartSquare.Name+chosen.TargetSquare.Name+(chosen.IsPromotion?(chosen.PromotionPieceType==PieceType.Knight?"n":chosen.PromotionPieceType.ToString()[0].ToString().ToLowerInvariant()):"");Send("info depth 0 pv "+uci);Send("bestmove "+uci);
  }catch(Exception error){Console.Error.WriteLine(error);Send("bestmove 0000");}
 }
}
