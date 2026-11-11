package app.boardlens.companion;

import java.util.*;

/**
 * Standard chess rules used only to validate captured positions and track legal changes. a1 = 0.
 */
public final class ChessPosition {
  final char[] b = new char[64];
  boolean white = true;
  String castle = "-";
  int ep = -1, half = 0, full = 1;

  public ChessPosition(String fen) {
    Arrays.fill(b, '.');
    String[] f = fen.trim().split(" +");
    String[] rows = f[0].split("/");
    if (rows.length != 8) throw new IllegalArgumentException("Eight ranks required");
    for (int r = 0; r < 8; r++) {
      int x = 0;
      for (char c : rows[r].toCharArray()) {
        if (c >= '1' && c <= '8') x += c - '0';
        else {
          if (x > 7 || "PNBRQKpnbrqk".indexOf(c) < 0)
            throw new IllegalArgumentException("Invalid piece");
          b[(7 - r) * 8 + x++] = c;
        }
      }
      if (x != 8) throw new IllegalArgumentException("Eight files required");
    }
    white = f.length < 2 || f[1].equals("w");
    castle = f.length > 2 ? f[2] : "-";
    ep = f.length > 3 && !f[3].equals("-") ? square(f[3]) : -1;
    half = f.length > 4 ? Integer.parseInt(f[4]) : 0;
    full = f.length > 5 ? Integer.parseInt(f[5]) : 1;
  }

  ChessPosition(ChessPosition p) {
    System.arraycopy(p.b, 0, b, 0, 64);
    white = p.white;
    castle = p.castle;
    ep = p.ep;
    half = p.half;
    full = p.full;
  }

  static int square(String s) {
    return s.charAt(0) - 'a' + (s.charAt(1) - '1') * 8;
  }

  static String name(int n) {
    return "" + (char) ('a' + n % 8) + (char) ('1' + n / 8);
  }

  static boolean color(char c) {
    return Character.isUpperCase(c);
  }

  String placement() {
    StringBuilder f = new StringBuilder();
    for (int r = 7; r >= 0; r--) {
      int n = 0;
      for (int x = 0; x < 8; x++) {
        char c = b[r * 8 + x];
        if (c == '.') n++;
        else {
          if (n > 0) {
            f.append(n);
            n = 0;
          }
          f.append(c);
        }
      }
      if (n > 0) f.append(n);
      if (r > 0) f.append('/');
    }
    return f.toString();
  }

  public String fen() {
    return placement()
        + " "
        + (white ? "w" : "b")
        + " "
        + (castle.isEmpty() ? "-" : castle)
        + " "
        + (ep < 0 ? "-" : name(ep))
        + " "
        + half
        + " "
        + full;
  }

  boolean attacked(int s, boolean byWhite) {
    int sx = s % 8, sy = s / 8;
    for (int from = 0; from < 64; from++) {
      char c = b[from];
      if (c == '.' || color(c) != byWhite) continue;
      int dx = sx - from % 8, dy = sy - from / 8, ax = Math.abs(dx), ay = Math.abs(dy);
      char p = Character.toLowerCase(c);
      if (p == 'p' && ax == 1 && dy == (byWhite ? 1 : -1)
          || p == 'n' && ax * ay == 2
          || p == 'k' && Math.max(ax, ay) == 1) return true;
      boolean line =
          (p == 'b' || p == 'q') && ax == ay && ax > 0
              || (p == 'r' || p == 'q') && (dx == 0 ^ dy == 0);
      if (line) {
        int step = Integer.signum(dx) + Integer.signum(dy) * 8, at = from + step;
        while (at != s && b[at] == '.') at += step;
        if (at == s) return true;
      }
    }
    return false;
  }

  boolean inCheck(boolean side) {
    for (int i = 0; i < 64; i++) if (b[i] == (side ? 'K' : 'k')) return attacked(i, !side);
    return true;
  }

  boolean valid() {
    int wk = 0, bk = 0;
    for (int i = 0; i < 64; i++) {
      char c = b[i];
      if (c == 'K') wk++;
      if (c == 'k') bk++;
      if ((i < 8 || i >= 56) && Character.toLowerCase(c) == 'p') return false;
    }
    return wk == 1 && bk == 1 && !inCheck(!white);
  }

  void add(List<String> out, int from, int to) {
    if (to < 0
        || to > 63
        || b[to] != '.' && color(b[to]) == white
        || Character.toLowerCase(b[to]) == 'k') return;
    if (Character.toLowerCase(b[from]) == 'p' && (to / 8 == 0 || to / 8 == 7)) {
      for (char p : "qrbn".toCharArray()) out.add(name(from) + name(to) + p);
    } else out.add(name(from) + name(to));
  }

  public List<String> legal() {
    List<String> moves = new ArrayList<>(), out = new ArrayList<>();
    for (int from = 0; from < 64; from++) {
      char c = b[from];
      if (c == '.' || color(c) != white) continue;
      int x = from % 8, y = from / 8;
      char p = Character.toLowerCase(c);
      if (p == 'p') {
        int dy = white ? 1 : -1, to = from + dy * 8;
        if (to >= 0 && to < 64 && b[to] == '.') {
          add(moves, from, to);
          if (y == (white ? 1 : 6) && b[from + dy * 16] == '.') add(moves, from, from + dy * 16);
        }
        for (int dx : new int[] {-1, 1}) {
          to = from + dy * 8 + dx;
          if (x + dx >= 0
              && x + dx < 8
              && to >= 0
              && to < 64
              && (b[to] != '.' && color(b[to]) != white || to == ep)) add(moves, from, to);
        }
      } else if (p == 'n' || p == 'k') {
        int[][] steps =
            p == 'n'
                ? new int[][] {
                  {1, 2}, {2, 1}, {-1, 2}, {-2, 1}, {1, -2}, {2, -1}, {-1, -2}, {-2, -1}
                }
                : new int[][] {
                  {1, 0}, {-1, 0}, {0, 1}, {0, -1}, {1, 1}, {1, -1}, {-1, 1}, {-1, -1}
                };
        for (int[] d : steps)
          if (x + d[0] >= 0 && x + d[0] < 8 && y + d[1] >= 0 && y + d[1] < 8)
            add(moves, from, from + d[0] + d[1] * 8);
        if (p == 'k' && from == (white ? 4 : 60) && !inCheck(white)) {
          int base = white ? 0 : 56;
          char rook = white ? 'R' : 'r';
          if (castle.indexOf(white ? 'K' : 'k') >= 0
              && b[base + 7] == rook
              && b[base + 5] == '.'
              && b[base + 6] == '.'
              && !attacked(base + 5, !white)
              && !attacked(base + 6, !white)) add(moves, from, base + 6);
          if (castle.indexOf(white ? 'Q' : 'q') >= 0
              && b[base] == rook
              && b[base + 1] == '.'
              && b[base + 2] == '.'
              && b[base + 3] == '.'
              && !attacked(base + 3, !white)
              && !attacked(base + 2, !white)) add(moves, from, base + 2);
        }
      } else {
        int[][] dirs = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}, {1, 1}, {1, -1}, {-1, 1}, {-1, -1}};
        for (int d = 0; d < 8; d++) {
          if (p == 'b' && d < 4 || p == 'r' && d >= 4) continue;
          int xx = x + dirs[d][0], yy = y + dirs[d][1];
          while (xx >= 0 && xx < 8 && yy >= 0 && yy < 8) {
            int to = yy * 8 + xx;
            add(moves, from, to);
            if (b[to] != '.') break;
            xx += dirs[d][0];
            yy += dirs[d][1];
          }
        }
      }
    }
    for (String m : moves) {
      ChessPosition next = play(m);
      if (!next.inCheck(white)) out.add(m);
    }
    return out;
  }

  public ChessPosition play(String move) {
    ChessPosition n = new ChessPosition(this);
    int f = square(move.substring(0, 2)), t = square(move.substring(2, 4));
    char piece = b[f];
    n.b[f] = '.';
    n.b[t] =
        move.length() > 4
            ? (white ? Character.toUpperCase(move.charAt(4)) : move.charAt(4))
            : piece;
    if (Character.toLowerCase(piece) == 'p' && t == ep && b[t] == '.')
      n.b[t + (white ? -8 : 8)] = '.';
    if (Character.toLowerCase(piece) == 'k' && Math.abs(t - f) == 2) {
      int rf = t > f ? f + 3 : f - 4, rt = t > f ? f + 1 : f - 1;
      n.b[rt] = n.b[rf];
      n.b[rf] = '.';
    }
    if (piece == 'K') n.castle = n.castle.replace("K", "").replace("Q", "");
    if (piece == 'k') n.castle = n.castle.replace("k", "").replace("q", "");
    int[] sq = {0, 7, 56, 63};
    String[] rights = {"Q", "K", "q", "k"};
    for (int i = 0; i < 4; i++)
      if (f == sq[i] || t == sq[i]) n.castle = n.castle.replace(rights[i], "");
    n.ep = Character.toLowerCase(piece) == 'p' && Math.abs(t - f) == 16 ? (f + t) / 2 : -1;
    n.half = Character.toLowerCase(piece) == 'p' || b[t] != '.' ? 0 : half + 1;
    n.full = full + (white ? 0 : 1);
    n.white = !white;
    return n;
  }

  String simple(String move) {
    int f = square(move.substring(0, 2)), t = square(move.substring(2, 4));
    String type =
        switch (Character.toLowerCase(b[f])) {
          case 'k' -> "King";
          case 'q' -> "Queen";
          case 'r' -> "Rook";
          case 'b' -> "Bishop";
          case 'n' -> "Knight";
          default -> "Pawn";
        };
    return (white ? "White: " : "Black: ")
        + type
        + " to "
        + name(t)
        + (move.length() > 4 ? " (promote to " + move.charAt(4) + ")" : "");
  }

  static ChessPosition sync(ChessPosition old, String placement, String turn) {
    if (old != null) {
      if (old.placement().equals(placement)) return old;
      for (String m : old.legal()) {
        ChessPosition n = old.play(m);
        if (n.placement().equals(placement)) return n;
        for (String reply : n.legal()) {
          ChessPosition nn = n.play(reply);
          if (nn.placement().equals(placement)) return nn;
        }
      }
    }
    String rights = placement.equals("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR") ? "KQkq" : "-";
    ChessPosition p =
        new ChessPosition(
            placement + " " + (turn.equals("Black") ? "b" : "w") + " " + rights + " - 0 1");
    if (!p.valid() && turn.equals("Auto")) {
      p.white = !p.white;
    }
    return p.valid() ? p : null;
  }
}
