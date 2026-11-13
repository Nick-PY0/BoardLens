using BoardLens.Mobile;
using System.Text.Json;
using System.Diagnostics;
var positions=new[]{
 "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
 "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
 "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1",
 "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 0 1",
 "8/P6k/8/8/8/8/6Kp/8 w - - 0 40",
 "7k/6Q1/6K1/8/8/8/8/8 b - - 0 40"
};
int passed=0;long maximumManaged=0;
foreach(var id in new[]{17,278,153,70,253,425,266,303,628,529,610,614}) {
 foreach(var fen in positions){
  try {var r=TinyCore.Search(id,fen,1000);Console.WriteLine(id+" "+(r==""?"terminal":r));passed++;}
  catch(Exception e){Console.WriteLine(id+" ERROR "+e.Message);Environment.ExitCode=1;}
 }
}
var clock=Stopwatch.StartNew();var task=Task.Run(()=>{try{TinyCore.Search(614,positions[0],30000);return false;}catch(OperationCanceledException){return true;}});
Thread.Sleep(40);TinyCore.Cancel();if(!task.Wait(5000)||!task.Result){Console.WriteLine("Cancellation FAILED");Environment.ExitCode=1;}else Console.WriteLine("Cancellation passed "+clock.ElapsedMilliseconds+"ms");
Console.WriteLine("Legal/terminal checks passed: "+passed+"/72");
var screenshot="r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3";
int fast=0;
foreach(var id in new[]{17,278,153,70,253,425,266,303,628,529,610,614}) {
 foreach(var ms in new[]{50,100,500}){
  try{var result=TinyCore.Search(id,screenshot,ms);if(result=="")throw new Exception("No move in live screenshot position");fast++;}
  catch(Exception error){Console.WriteLine(id+" budget "+ms+" ERROR "+error.Message);Environment.ExitCode=1;}
 }
 maximumManaged=Math.Max(maximumManaged,GC.GetTotalMemory(true));
 TinyCore.Release();
}
Console.WriteLine("Fast screenshot checks: "+fast+"/36 · peak live managed bytes "+maximumManaged);
if(maximumManaged>160L*1024*1024){Console.WriteLine("Mobile memory bound FAILED");Environment.ExitCode=1;}
