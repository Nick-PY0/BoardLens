package app.boardlens.companion;

import android.content.*;
import android.database.*;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.*;

/** Read-only grant for the one verified update; no general filesystem access. */
public final class UpdateProvider extends ContentProvider {
    @Override public boolean onCreate(){return true;}
    private File file(Uri uri)throws FileNotFoundException{
        if(!"/package.apk".equals(uri.getPath())||!uri.getAuthority().equals(getContext().getPackageName()+".updates"))throw new FileNotFoundException();
        File file=new File(getContext().getCacheDir(),"update.apk");if(!file.isFile())throw new FileNotFoundException();return file;
    }
    @Override public ParcelFileDescriptor openFile(Uri uri,String mode)throws FileNotFoundException{if(!"r".equals(mode))throw new FileNotFoundException();return ParcelFileDescriptor.open(file(uri),ParcelFileDescriptor.MODE_READ_ONLY);}
    @Override public String getType(Uri uri){return "application/vnd.android.package-archive";}
    @Override public Cursor query(Uri uri,String[] projection,String selection,String[] args,String sort){try{File file=file(uri);String[] columns=projection==null?new String[]{OpenableColumns.DISPLAY_NAME,OpenableColumns.SIZE}:projection;MatrixCursor cursor=new MatrixCursor(columns);Object[] values=new Object[columns.length];for(int i=0;i<columns.length;i++)values[i]=OpenableColumns.DISPLAY_NAME.equals(columns[i])?"BoardLens-update.apk":OpenableColumns.SIZE.equals(columns[i])?file.length():null;cursor.addRow(values);return cursor;}catch(FileNotFoundException error){return null;}}
    @Override public Uri insert(Uri uri,ContentValues values){throw new UnsupportedOperationException();}
    @Override public int delete(Uri uri,String selection,String[] args){throw new UnsupportedOperationException();}
    @Override public int update(Uri uri,ContentValues values,String selection,String[] args){throw new UnsupportedOperationException();}
}
