package app.boardlens.companion;

import android.content.Context;
import android.content.SharedPreferences;

/** Deliberately separate from computer companion preferences. */
final class PhoneSettings {
  final SharedPreferences p;

  PhoneSettings(Context c) {
    this(c,"phone-screen");
  }

  PhoneSettings(Context c,String name){p=c.getSharedPreferences(name,0);}

  float seconds() {
    return p.getFloat("seconds", .5f);
  }

  float evaluationSeconds(){return Math.max(.03f,Math.min(30f,p.getFloat("evaluation_seconds",.2f)));}
  int evaluationDepth(){return Math.max(1,Math.min(40,p.getInt("evaluation_depth",18)));}
  boolean evaluationEnabled(){return p.getBoolean("evaluation_enabled",true);}
  boolean screenEvaluation(){return p.getBoolean("screen_evaluation",true);}
  String evaluationPosition(){return p.getString("evaluation_position","Auto");}

  int depth() {
    return p.getInt("depth", 18);
  }

  int moves() {
    return p.getInt("moves", 1);
  }

  int threads() {
    return p.getInt("threads", 1);
  }

  int skill() {
    return p.getInt("skill", 20);
  }

  boolean arrows() {
    return p.getBoolean("arrows", true);
  }

  boolean steady() {
    return p.getBoolean("steady", true);
  }

  boolean lockMove(){ return p.getBoolean("lock_move",false); }

  boolean predict() {
    return p.getBoolean("predict", true);
  }

  int predictionPlies() { return p.getInt("prediction_plies", 3); }

  float predictionSeconds() { return p.getFloat("prediction_seconds", 3f); }

  boolean early() { return p.getBoolean("early", true); }

  boolean onlyMine() {
    return p.getBoolean("onlyMine", false);
  }

  String orientation() {
    return p.getString("orientation", "Auto");
  }

  String turn() {
    return p.getString("turn", "Auto");
  }

  String mode() {
    return p.getString("mode", "Time + depth");
  }

  int rating() { return p.getInt("rating",1500); }

  String backend() { return "On phone"; }

  String engine() {
    return p.getString("engine", "stockfish");
  }

  String evaluator() {
    return p.getString("evaluator", "stockfish");
  }
}
