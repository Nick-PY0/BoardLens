package app.boardlens.companion;

/** Confirm unchanged board pixels without running neural recognition a second time. */
final class ReadConfirmation<T> {
 private T candidate;private int[] fingerprint;private long since;
 void set(T read,int[] pixels,long now){candidate=read;fingerprint=pixels.clone();since=now;}
 T poll(int[] pixels,long now){if(candidate==null)return null;if(different(fingerprint,pixels)){clear();return null;}return now-since>=24?candidate:null;}
 void clear(){candidate=null;fingerprint=null;}
 static boolean different(int[] a,int[] b){
  if(a==null||b==null||a.length!=b.length)return true;int changed=0,total=0;
  for(int i=0;i<a.length;i++){if(a[i]==0||b[i]==0)continue;total++;int x=a[i],y=b[i];if(Math.abs((x>>16&255)-(y>>16&255))+Math.abs((x>>8&255)-(y>>8&255))+Math.abs((x&255)-(y&255))>30)changed++;}
  return changed>Math.max(6,total*.0005);
 }
}
