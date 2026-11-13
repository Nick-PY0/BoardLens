package app.boardlens.companion;

/** Confirm quiet pixels cheaply, or matching piece reads despite animated highlights. */
final class ReadConfirmation<T> {
 private T candidate;private int[] fingerprint;private long since;private boolean changed;
 void set(T read,int[] pixels,long now){candidate=read;fingerprint=pixels.clone();since=now;changed=false;}
 boolean pending(){return candidate!=null&&!changed;}
 T poll(int[] pixels,long now){if(candidate==null||changed)return null;if(different(fingerprint,pixels)){changed=true;return null;}return now-since>=24?candidate:null;}
 boolean agrees(T read,long now,java.util.function.BiPredicate<T,T> same){return candidate!=null&&now-since>=24&&same.test(candidate,read);}
 void clear(){candidate=null;fingerprint=null;changed=false;}
 static boolean different(int[] a,int[] b){
  if(a==null||b==null||a.length!=b.length)return true;int changed=0,total=0;
  for(int i=0;i<a.length;i++){if(a[i]==0||b[i]==0)continue;total++;int x=a[i],y=b[i];if(Math.abs((x>>16&255)-(y>>16&255))+Math.abs((x>>8&255)-(y>>8&255))+Math.abs((x&255)-(y&255))>30)changed++;}
  return changed>Math.max(6,total*.0005);
 }
}
