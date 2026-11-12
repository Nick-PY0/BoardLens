package app.boardlens.companion;
import android.content.Context;
import java.util.*;

final class EngineCatalog {
 record Entry(String id,String name,String kind,String detail){boolean tiny(){return kind.equals("tiny");}boolean maia(){return kind.equals("maia");}}
 static final List<Entry> ALL=java.util.Arrays.asList(
  new Entry("stockfish","Stockfish","stockfish","Strongest analysis · local engine"),
  new Entry("lc0","LC0 · CPU","lc0","Leela Chess Zero · optional network · CPU search"),
  new Entry("maia3-5m","Maia 3 · 5M","maia","Human moves · smallest Maia 3 model"),
  new Entry("maia3-23m","Maia 3 · 23M","maia","Human moves · optional larger model"),
  new Entry("maia3-79m","Maia 3 · 79M","maia","Human moves · large optional model"),
  new Entry("maia2","Maia 2 · Rapid","maia","Human moves · rating-conditioned"),
  new Entry("flounder","Flounder · Stockfish-based","stockfish","Adjustable strength using Stockfish"),
  new Entry("tiny17","The CopyCat","tiny","Absolute beginner · original reference rating 192"),
  new Entry("tiny278","Bongcloud Enthusiast","tiny","Easy · original reference rating 307"),
  new Entry("tiny153","WhateverBot","tiny","Casual · original reference rating 677"),
  new Entry("tiny70","applemethod-orz","tiny","Intermediate · original reference rating 1085"),
  new Entry("tiny253","Squeedo","tiny","Challenging · original reference rating 1276"),
  new Entry("tiny425","200 Tokens Monstrosity","tiny","Advanced · original reference rating 1569"),
  new Entry("tiny266","Game Tech Explained","tiny","Expert · original reference rating 1713"),
  new Entry("tiny303","Electric Shockwave Gambit","tiny","Master · original reference rating 2001"),
  new Entry("tiny628","King Gambot IV","tiny","Strong master · original reference rating 2172"),
  new Entry("tiny529","NNBot","tiny","Elite · original reference rating 2246"),
  new Entry("tiny610","TinyHugeBot","tiny","Grandmaster · original reference rating 2513"),
  new Entry("tiny614","Boychesser","tiny","Strong tournament bot · reference rating 2772"));
 static Entry get(String id){if(id.equals("maia3"))id="maia3-5m";for(Entry e:ALL)if(e.id.equals(id))return e;return ALL.get(0);}
 static boolean ready(Context c,String id){Entry e=get(id);return e.tiny()?TinyLocal.available():(e.maia()||e.kind().equals("lc0"))?PhoneModels.ready(c,e.id):EngineFiles.ready(c);}
}
