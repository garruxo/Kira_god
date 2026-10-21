package org.kira.servicio;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;
import android.provider.OpenableColumns;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * Archivos que entran y salen de Kira:
 *  - guardarEnDescargas(ctx, ruta, nombre, tipo): copia un archivo de Kira (un PDF) a Descargas/Kira del móvil.
 *  - leerIntent(ctx, intent, carpeta): lo que te han COMPARTIDO con Kira desde otra app (un enlace o un PDF).
 *    Devuelve "texto\n<texto>", "archivo\n<ruta copiada>\n<nombre>" o "" si no hay nada.
 */
public class ArchivosKira {
    private static final long MAXIMO = 150L * 1024 * 1024;

    public static boolean guardarEnDescargas(Context ctx, String ruta, String nombre, String tipo) {
        InputStream in = null;
        OutputStream out = null;
        try {
            in = new FileInputStream(ruta);
            if (Build.VERSION.SDK_INT >= 29) {
                ContentValues v = new ContentValues();
                v.put(MediaStore.MediaColumns.DISPLAY_NAME, nombre);
                v.put(MediaStore.MediaColumns.MIME_TYPE, tipo);
                v.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Kira");
                Uri uri = ctx.getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v);
                if (uri == null) return false;
                out = ctx.getContentResolver().openOutputStream(uri);
            } else {
                File dir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "Kira");
                if (!dir.exists() && !dir.mkdirs()) return false;
                out = new FileOutputStream(new File(dir, nombre));
            }
            if (out == null) return false;
            copiar(in, out, Long.MAX_VALUE);
            return true;
        } catch (Throwable t) {
            return false;
        } finally {
            try { if (in != null) in.close(); } catch (Exception e) { }
            try { if (out != null) out.close(); } catch (Exception e) { }
        }
    }

    public static String leerIntent(Context ctx, Intent intent, String carpeta) {
        try {
            if (intent == null) return "";
            String accion = intent.getAction();
            Uri uri = null;
            if (Intent.ACTION_SEND.equals(accion)) {
                Object s = intent.getParcelableExtra(Intent.EXTRA_STREAM);
                if (s instanceof Uri) uri = (Uri) s;
                if (uri == null) {
                    CharSequence t = intent.getCharSequenceExtra(Intent.EXTRA_TEXT);
                    if (t != null && t.length() > 0) return "texto\n" + t.toString();
                }
            } else if (Intent.ACTION_VIEW.equals(accion)) {
                uri = intent.getData();
                if (uri != null && ("http".equals(uri.getScheme()) || "https".equals(uri.getScheme()))) {
                    return "texto\n" + uri.toString();
                }
            }
            if (uri == null) return "";
            String nombre = nombreDe(ctx, uri);
            File dir = new File(carpeta);
            if (!dir.exists() && !dir.mkdirs()) return "";
            File destino = new File(dir, "compartido_" + System.currentTimeMillis() + ".pdf");
            InputStream in = null;
            OutputStream out = null;
            try {
                if ("file".equals(uri.getScheme())) {
                    in = new FileInputStream(new File(uri.getPath()));
                } else {
                    in = ctx.getContentResolver().openInputStream(uri);
                }
                if (in == null) return "";
                out = new FileOutputStream(destino);
                if (!copiar(in, out, MAXIMO)) {
                    destino.delete();
                    return "";
                }
            } finally {
                try { if (in != null) in.close(); } catch (Exception e) { }
                try { if (out != null) out.close(); } catch (Exception e) { }
            }
            return "archivo\n" + destino.getAbsolutePath() + "\n" + nombre;
        } catch (Throwable t) {
            return "";
        }
    }

    private static String nombreDe(Context ctx, Uri uri) {
        String nombre = "";
        Cursor c = null;
        try {
            if (ContentResolver.SCHEME_CONTENT.equals(uri.getScheme())) {
                c = ctx.getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null);
                if (c != null && c.moveToFirst()) nombre = c.getString(0);
            }
        } catch (Throwable t) {
            nombre = "";
        } finally {
            if (c != null) c.close();
        }
        if (nombre == null || nombre.length() == 0) {
            String ultimo = uri.getLastPathSegment();
            nombre = ultimo == null ? "documento" : ultimo;
        }
        return nombre.replace('\n', ' ');
    }

    private static boolean copiar(InputStream in, OutputStream out, long maximo) throws java.io.IOException {
        byte[] b = new byte[64 * 1024];
        long total = 0;
        int n;
        while ((n = in.read(b)) > 0) {
            total += n;
            if (total > maximo) return false;
            out.write(b, 0, n);
        }
        return true;
    }
}
