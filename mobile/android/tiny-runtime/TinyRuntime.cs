using Android.Runtime;
using Java.Interop;
namespace BoardLens.Mobile;
[Register("app/boardlens/companion/TinyRuntime")]
[Preserve(AllMembers=true)]
public class TinyRuntime:Java.Lang.Object {
 [Export] public TinyRuntime(){}
 [Export("search")] public string Search(int id,string fen,int milliseconds) { try { return TinyCore.Search(id,fen,milliseconds); } catch(Exception error) { return System.Text.Json.JsonSerializer.Serialize(new { error=error.Message, cancelled=error is OperationCanceledException }); } }
 [Export("cancel")] public void Cancel()=>TinyCore.Cancel();
}
