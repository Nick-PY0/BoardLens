using ChessChallenge.API;
using System.Diagnostics;
using System.Text.Json;

namespace BoardLens.Mobile;
public static class TinyBudget {
 static long generation;
 [ThreadStatic] static long token;
 [ThreadStatic] static long deadline;
 public static long Token()=>Interlocked.Read(ref generation);
 public static void Begin(int milliseconds,long captured) { token=captured;deadline=Stopwatch.GetTimestamp()+(long)((milliseconds+200)/1000.0*Stopwatch.Frequency); }
 public static void Cancel() => Interlocked.Increment(ref generation);
 public static void Check() {
  if(deadline==0)return;
  if(token!=Interlocked.Read(ref generation))throw new OperationCanceledException("Analysis cancelled");
  if(Stopwatch.GetTimestamp()>deadline)throw new TimeoutException("Bot exceeded the thinking budget. Increase its think time.");
 }
 public static void End()=>deadline=0;
}

public static class TinyCore {
 static readonly Dictionary<bool,IChessBot> instances=new();
 static int selected=-1;
 static IChessBot Create(int id)=>id switch {
  17=>new auto_Bot_17.Bot_17(),278=>new auto_Bot_278.Bot_278(),153=>new auto_Bot_153.Bot_153(),70=>new auto_Bot_70.Bot_70(),253=>new auto_Bot_253.Bot_253(),425=>new auto_Bot_425.Bot_425(),266=>new auto_Bot_266.MyBot(),303=>new auto_Bot_303.Bot_303(),628=>new auto_Bot_628.Bot_628(),529=>new auto_Bot_529.Bot_529(),610=>new auto_Bot_610.Bot_610(),614=>new auto_Bot_614.Bot_614(),_=>throw new ArgumentException("Unknown Tiny engine")};
 public static string Search(int id,string fen,int milliseconds) {
  long requested=TinyBudget.Token();
  lock(instances) {
   if(selected!=id){instances.Clear();selected=id;GC.Collect();}
   var core=new ChessChallenge.Chess.Board();core.LoadPosition(fen);var board=new ChessChallenge.API.Board(core);
   if(!instances.TryGetValue(board.IsWhiteToMove,out var bot)){bot=Create(id);instances[board.IsWhiteToMove]=bot;}
   var legal=board.GetLegalMoves();if(legal.Length==0)return "";
   milliseconds=Math.Clamp(milliseconds,50,30000);var watch=Stopwatch.StartNew();
   TinyBudget.Begin(milliseconds,requested);
   try {
    TinyBudget.Check();var chosen=bot.Think(board,new ChessChallenge.API.Timer(milliseconds*10,milliseconds*10,milliseconds*10,0));
    TinyBudget.Check();if(!legal.Any(m=>m.RawValue==chosen.RawValue))throw new InvalidOperationException("The selected bot did not return a legal move");
    string move=chosen.StartSquare.Name+chosen.TargetSquare.Name+(chosen.IsPromotion?chosen.PromotionPieceType switch{PieceType.Queen=>"q",PieceType.Rook=>"r",PieceType.Bishop=>"b",_=>"n"}:"");
    return JsonSerializer.Serialize(new{move,elapsed_ms=watch.ElapsedMilliseconds,engine="tiny"+id});
   } finally { TinyBudget.End(); }
  }
 }
 public static void Cancel()=>TinyBudget.Cancel();
}
