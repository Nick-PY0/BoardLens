package app.boardlens.companion;

import android.app.Activity;
import android.os.*;
import android.graphics.*;
import android.view.*;
import android.webkit.*;
import android.widget.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import org.json.*;

/** Isolated local view/model test: no capture, overlay, service, engines or network permission. */
public class ComponentActivity extends Activity {
 @Override public void onCreate(Bundle state){super.onCreate(state);getWindow().setStatusBarColor(MobileUi.BG);getWindow().setNavigationBarColor(MobileUi.BG);
  String page=getIntent().getStringExtra("page");
  if("reader".equals(page)){TextView t=new TextView(this);t.setText("Testing local fixtures…");setContentView(t);new Thread(()->readFixtures(t)).start();return;}
  if("companion".equals(page)){companion();return;}
  PhoneDashboard d=new PhoneDashboard(this,new PhoneDashboard.Actions(){
   public void start(){}public void stop(){}public void hide(){}public void scan(){}public void settings(){}public void help(){}public void back(){}public boolean option(String k,boolean f){return f;}public void option(String k,boolean v,boolean unused){}
  });
  d.render(true,"Board found · watching for moves","Knight to f3","Stockfish · +0.31",.53f,null);inset(d.root);setContentView(d.root);
 }
 void inset(View v){getWindow().setDecorFitsSystemWindows(false);v.setOnApplyWindowInsetsListener((view,i)->{android.graphics.Insets s=i.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());view.setPadding(s.left,s.top,s.right,s.bottom);return WindowInsets.CONSUMED;});v.requestApplyInsets();}
 void companion(){WebView web=new WebView(this);web.setBackgroundColor(MobileUi.BG);web.getSettings().setJavaScriptEnabled(true);web.getSettings().setDomStorageEnabled(true);web.setWebViewClient(new WebViewClient(){
  @Override public WebResourceResponse shouldInterceptRequest(WebView v,WebResourceRequest request){try{String path=request.getUrl().getPath();if(path.startsWith("/api/")){String body=path.equals("/api/state")?asset("fixture-state.json"):"{\"result\":\"Test component\"}";return response("application/json",body.getBytes(StandardCharsets.UTF_8));}String name=path.equals("/")?"index.html":path.substring(1);String mime=name.endsWith("css")?"text/css":name.endsWith("js")?"application/javascript":name.endsWith("png")?"image/png":"text/html";return response(mime,getAssets().open("companion/"+name).readAllBytes());}catch(Exception e){return response("text/plain",new byte[0]);}}
  @Override public void onPageFinished(WebView view,String url){view.evaluateJavascript("localStorage.setItem('boardlens-token','component-test');token='component-test';refresh(true);",null);new Handler().postDelayed(()->view.evaluateJavascript("JSON.stringify({width:innerWidth,scroll:document.documentElement.scrollWidth,buttons:[...document.querySelectorAll('button:not([hidden])')].filter(b=>b.getBoundingClientRect().width>innerWidth).length,phoneMenu:!document.getElementById('phone-menu').hidden})",result->write("layout.json",result)),1200);}
 });
 web.addJavascriptInterface(new Object(){@JavascriptInterface public void openPhoneScreen(){}@JavascriptInterface public void pairedToken(String token){}},"BoardLensDevice");FrameLayout frame=new FrameLayout(this);frame.setBackgroundColor(MobileUi.BG);frame.addView(web,new FrameLayout.LayoutParams(-1,-1));inset(frame);setContentView(frame);web.loadUrl("https://component.test/");
 }
 WebResourceResponse response(String mime,byte[] data){return new WebResourceResponse(mime,"UTF-8",new ByteArrayInputStream(data));}
 String asset(String name)throws Exception{try(InputStream in=getAssets().open(name)){return new String(in.readAllBytes(),StandardCharsets.UTF_8);}}
 void write(String name,String value){try(FileOutputStream out=openFileOutput(name,0)){out.write(value.getBytes(StandardCharsets.UTF_8));}catch(Exception e){throw new RuntimeException(e);}}
 void readFixtures(TextView status){try(BoardReader reader=new BoardReader(this)){JSONArray cases=new JSONArray(asset("reader-fixtures.json")),results=new JSONArray();for(int i=0;i<cases.length();i++){JSONObject item=cases.getJSONObject(i);Bitmap image;try(InputStream in=getAssets().open("fixtures/"+item.getString("image"))){image=BitmapFactory.decodeStream(in);}long start=System.nanoTime();BoardReader.Read read=reader.read(image,null,item.optString("orientation","White at bottom"));JSONObject row=new JSONObject().put("image",item.getString("image")).put("expected",item.getString("placement")).put("found",read!=null).put("ms",(System.nanoTime()-start)/1e6).put("diagnostic",reader.diagnostic);if(read==null){JSONArray candidates=new JSONArray();try(ContextPieces context=new ContextPieces(this)){for(android.graphics.Rect rect:GradientBoards.detectProjected(image)){BoardGeometry g=BoardGeometry.rectangle(rect.left,rect.top,rect.right,rect.bottom);BoardReader.Read result=context.classify(image,g,"White at bottom");candidates.put(new JSONObject().put("rect",rect.toShortString()).put("read",result==null?"uncertain":result.placement()));}}row.put("candidates",candidates);}if(item.has("corners")){JSONArray corners=item.getJSONArray("corners");double[] points=new double[8];for(int n=0;n<8;n++)points[n]=corners.getDouble(n);BoardGeometry geometry=new BoardGeometry(points);try(ContextPieces context=new ContextPieces(this)){BoardReader.Read exact=context.classify(image,geometry,item.optString("orientation","White at bottom"));row.put("known_geometry",exact==null?"uncertain":exact.placement()).put("grid",ProjectedBoards.checker(image,geometry));}}if(item.has("rect")){JSONArray rect=item.getJSONArray("rect");BoardGeometry geometry=BoardGeometry.rectangle(rect.getDouble(0),rect.getDouble(1),rect.getDouble(0)+rect.getDouble(2),rect.getDouble(1)+rect.getDouble(3));try(ContextPieces context=new ContextPieces(this)){BoardReader.Read exact=context.classify(image,geometry,item.optString("orientation","White at bottom"));row.put("known_geometry",exact==null?"uncertain":exact.placement()).put("grid",ProjectedBoards.checker(image,geometry));}}if(read!=null){long warm=System.nanoTime();reader.read(image,read.rect(),item.optString("orientation","White at bottom"));row.put("warm_ms",(System.nanoTime()-warm)/1e6);}if(read!=null)row.put("placement",read.placement()).put("confidence",read.confidence()).put("exact",read.placement().equals(item.getString("placement")));results.put(row);if(i%5==0)write("reader-progress.json",results.toString());image.recycle();}write("reader-results.json",results.toString(2));runOnUiThread(()->status.setText("Fixture results saved"));}catch(Exception e){write("reader-error.txt",e.toString());runOnUiThread(()->status.setText(e.toString()));}}
}
