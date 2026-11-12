package app.boardlens.companion;

import static org.junit.Assert.*;

import org.junit.Test;

public class ChessPositionTest {
  long perft(ChessPosition p, int depth) {
    if (depth == 0) return 1;
    long n = 0;
    for (String m : p.legal()) n += perft(p.play(m), depth - 1);
    return n;
  }

  @Test
  public void initialPerft() {
    ChessPosition p = new ChessPosition("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    assertEquals(8902, perft(p, 3));
    assertEquals(20, p.legal().size());
  }

  @Test
  public void castlingAndPins() {
    ChessPosition p =
        new ChessPosition("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1");
    assertEquals(48, p.legal().size());
    assertEquals(2039, perft(p, 2));
    assertTrue(p.legal().contains("e1g1"));
  }

  @Test
  public void legalSyncRetainsHistory() {
    ChessPosition p = new ChessPosition("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    ChessPosition next = p.play("e2e4").play("c7c5");
    assertEquals(next.fen(), ChessPosition.sync(p, next.placement(), "Auto").fen());
    assertFalse(ChessPosition.sync(p, p.play("e2e4").placement(), "White").white);
  }

  @Test
  public void everySingleMovePreservesTurnAndRightsBeforeSkippedFrameSearch() {
    ChessPosition board = new ChessPosition("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    for (String move : board.legal()) {
      ChessPosition next = board.play(move);
      assertEquals(next.fen(), ChessPosition.sync(board, next.placement(), "Auto").fen());
    }
    ChessPosition castle = new ChessPosition("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 3 21");
    assertEquals(castle.play("e1g1").fen(), ChessPosition.sync(castle, castle.play("e1g1").placement(), "Auto").fen());
  }

  @Test
  public void enPassantCannotExposeKing() {
    ChessPosition p = new ChessPosition("8/6bb/8/8/R1pP2k1/4P3/P7/K7 b - d3 0 1");
    assertFalse(p.legal().contains("c4d3"));
  }
}
