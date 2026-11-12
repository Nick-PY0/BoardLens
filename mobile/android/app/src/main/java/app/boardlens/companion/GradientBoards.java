package app.boardlens.companion;

import android.graphics.*;
import java.util.*;

/** Gradient-grid method adapted from Fenshot / tensorflow_chessbot (MIT notices in assets). */
final class GradientBoards {
  static List<int[]> sequences(double[] response) {return sequences(response,7);}

  static List<int[]> sequences(double[] response,int minimum) {
    double max = 0;
    for (double v : response) max = Math.max(max, v);
    List<Integer> peaks = new ArrayList<>();
    for (int i = 0; i < response.length; i++) {
      double nearby = 0;
      for (int j = Math.max(0, i - 4); j <= Math.min(response.length - 1, i + 4); j++)
        nearby = Math.max(nearby, response[j]);
      if (response[i] >= nearby && response[i] > max * (minimum<7?.05:.17)) peaks.add(i);
    }
    if (peaks.size() > 100) {
      peaks.sort((a, b) -> Double.compare(response[b], response[a]));
      peaks = new ArrayList<>(peaks.subList(0, 100));
      Collections.sort(peaks);
    }
    Map<String, int[]> unique = new HashMap<>();
    for (int i = 0; i < peaks.size() - minimum+1; i++)
      for (int j = i + 1; j < peaks.size(); j++) {
        int first = peaks.get(i), second = peaks.get(j), space = second - first;
        if (space < 12) continue;
        if (first + (minimum-1) * space > response.length + 5) break;
        List<Integer> line = new ArrayList<>();
        line.add(first);
        line.add(second);
        while (true) {
          int target = line.get(line.size() - 1) + space,
              at = Collections.binarySearch(peaks, target);
          if (at < 0) at = -at - 1;
          int nearest = -1, delta = Integer.MAX_VALUE;
          for (int k = Math.max(0, at - 1); k <= Math.min(peaks.size() - 1, at); k++) {
            int candidate = peaks.get(k), d = Math.abs(candidate - target);
            if (d < delta) {
              nearest = candidate;
              delta = d;
            }
          }
          if (nearest < 0
              || delta >= Math.max(3, space * .045)
              || nearest <= line.get(line.size() - 1)) break;
          line.add(nearest);
        }
        if (line.size() >= minimum) {
          int[] arr = new int[line.size()];
          for (int k = 0; k < arr.length; k++) arr[k] = line.get(k);
          unique.put(line.toString(), arr);
        }
      }
    List<int[]> lines = new ArrayList<>(unique.values());
    lines.sort((a, b) -> Double.compare(strength(b, response), strength(a, response)));
    return lines.subList(0, Math.min(8, lines.size()));
  }

  static double strength(int[] line, double[] response) {
    double total = 0;
    for (int v : line) total += response[v];
    return total / line.length;
  }

  static List<int[]> extents(List<int[]> lines) {
    List<int[]> result = new ArrayList<>();
    for (int[] line : lines) {
      int[] gaps = new int[line.length - 1];
      for (int i = 0; i < gaps.length; i++) gaps[i] = line[i + 1] - line[i];
      Arrays.sort(gaps);
      float space = gaps[gaps.length / 2];
      for (int i = 0; i < line.length - 6; i++)
        result.add(new int[] {Math.round(line[i] - space), Math.round(line[i + 6] + space)});
    }
    return result;
  }

  static List<int[]> projectedExtents(List<int[]> lines){
    List<int[]> result=new ArrayList<>();for(int[] line:lines){int[] gaps=new int[line.length-1];for(int i=0;i<gaps.length;i++)gaps[i]=line[i+1]-line[i];Arrays.sort(gaps);int cell=gaps[gaps.length/2];for(int i=0;i<=line.length-5;i++)for(int padding=0;padding<=4;padding++)result.add(new int[]{line[i]-padding*cell,line[i]+(8-padding)*cell});}return result;
  }

  static List<Rect> detect(Bitmap image) {return detect(image,false);}
  static List<Rect> detectFast(Bitmap image){return detect(image,false,960);}
  static List<Rect> detectProjected(Bitmap image){return detect(image,true);}
  private static List<Rect> detect(Bitmap image,boolean projected) {return detect(image,projected,1600);}
  private static List<Rect> detect(Bitmap image,boolean projected,int maximum) {
    float scale = Math.min(1f, maximum / (float)Math.max(image.getWidth(), image.getHeight()));
    Bitmap small =
        Bitmap.createScaledBitmap(
            image,
            Math.round(image.getWidth() * scale),
            Math.round(image.getHeight() * scale),
            true);
    int w = small.getWidth(), h = small.getHeight();
    int[] pixels = new int[w * h];
    small.getPixels(pixels, 0, w, 0, 0, w, h);
    if (small != image) small.recycle();
    float[] gray = new float[pixels.length];
    for (int i = 0; i < pixels.length; i++)
      gray[i] =
          Color.red(pixels[i]) * .299f
              + Color.green(pixels[i]) * .587f
              + Color.blue(pixels[i]) * .114f;
    double[] xp = new double[w], xn = new double[w], yp = new double[h], yn = new double[h];
    for (int y = 1; y < h - 1; y++)
      for (int x = 1; x < w - 1; x++) {
        int at = y * w + x;
        float gx = (gray[at + 1] - gray[at - 1]) * .5f, gy = (gray[at + w] - gray[at - w]) * .5f;
        if (gx > 0) xp[x] += gx;
        else xn[x] -= gx;
        if (gy > 0) yp[y] += gy;
        else yn[y] -= gy;
      }
    for (int x = 0; x < w; x++) xp[x] *= xn[x];
    for (int y = 0; y < h; y++) yp[y] *= yn[y];
    List<int[]> xs = projected?projectedExtents(sequences(xp,5)):extents(sequences(xp)), ys = projected?projectedExtents(sequences(yp,5)):extents(sequences(yp));
    List<Rect> boxes = new ArrayList<>();
    Map<Rect, Double> scores = new HashMap<>();
    for (int[] xx : xs)
      for (int[] yy : ys) {
        int width=xx[1]-xx[0],height=yy[1]-yy[0],size=Math.round((width+height)/2f);
        if(size<160||xx[0]<0||yy[0]<0||xx[1]>w||yy[1]>h)continue;
        if(projected?(height/(float)width<.65||height/(float)width>1.1):Math.abs(width-height)>size*.025)continue;
        int x=projected?xx[0]:Math.round((xx[0]+xx[1]-size)/2f),y=projected?yy[0]:Math.round((yy[0]+yy[1]-size)/2f);
        double score=projected?ProjectedBoards.checker(image,BoardGeometry.rectangle(x/scale,y/scale,(x+width)/scale,(y+height)/scale)):BoardReader.checker(pixels,w,h,x,y,size);
        if(score<(projected?.82:.65))continue;
        boolean duplicate = false;
        for (Rect r : boxes)
          if (Math.abs(r.left - x) < size * .035
              && Math.abs(r.top - y) < size * .035
              && Math.abs(r.width() - size) < size * .035) duplicate = true;
        if (!duplicate) {
          Rect r = new Rect(x,y,x+(projected?width:size),y+(projected?height:size));
          boxes.add(r);
          scores.put(r, score);
        }
      }
    boxes.sort((a, b) -> Double.compare(scores.get(b), scores.get(a)));
    List<Rect> result = new ArrayList<>();
    for (Rect r : boxes.subList(0, Math.min(8, boxes.size())))
      result.add(
          new Rect(
              Math.round(r.left / scale),
              Math.round(r.top / scale),
              Math.round(r.right / scale),
              Math.round(r.bottom / scale)));
    return result;
  }
}
