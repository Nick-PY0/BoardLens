// TinyHugeBot by Popax21 and atpx8, MIT challenge submission.
// Normal C# compilation: no runtime decoder or AssemblyResolve hook.
// Reproduction and mobile adaptations: ../Vendor/TinyHuge/README.md.
namespace auto_Bot_610;
using ChessChallenge.API;
class Bot_610 : IChessBot {
    private readonly IChessBot original=new auto_Bot_610_original.Search();
    public Move Think(Board board,Timer timer)=>original.Think(board,timer);
}
