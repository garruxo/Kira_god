package org.kira.servicio;

import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.Typeface;
import android.graphics.drawable.Icon;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;

import java.io.FileInputStream;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * Tus juegos de Kira como apps:
 *  - ponerEnInicio(act, id, nombre, color): un icono en la pantalla de inicio que abre Kira DIRECTAMENTE en ese juego
 *    (el intent lleva el extra "kira_juego" = id). Devuelve "ok", "no" (el lanzador no deja) o "viejo" (Android < 8).
 *  - abrirHtml(act, ruta, nombre): copia la página del juego a Descargas/Kira y la abre en el navegador.
 *    Devuelve "abierto", "guardado" (se guardó pero no hay navegador que la abra) o "" si falló.
 */
public class AppsKira {

    public static String ponerEnInicio(Activity act, String id, String nombre, int color) {
        try {
            if (Build.VERSION.SDK_INT < 26) return "viejo";
            ShortcutManager sm = act.getSystemService(ShortcutManager.class);
            if (sm == null || !sm.isRequestPinShortcutSupported()) return "no";
            Intent abrir = new Intent(Intent.ACTION_MAIN);
            abrir.setClassName(act.getPackageName(), "org.kivy.android.PythonActivity");
            abrir.putExtra("kira_juego", id);
            abrir.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            String etiqueta = nombre.length() > 24 ? nombre.substring(0, 24) : nombre;
            ShortcutInfo info = new ShortcutInfo.Builder(act, "juego_" + id)
                    .setShortLabel(etiqueta)
                    .setLongLabel(nombre.length() > 60 ? nombre.substring(0, 60) : nombre)
                    .setIcon(Icon.createWithBitmap(icono(nombre, color)))
                    .setIntent(abrir)
                    .build();
            return sm.requestPinShortcut(info, null) ? "ok" : "no";
        } catch (Throwable t) {
            return "no";
        }
    }

    /** Un icono sencillo: un círculo del color del juego con su inicial. */
    private static Bitmap icono(String nombre, int color) {
        int lado = 192;
        Bitmap bmp = Bitmap.createBitmap(lado, lado, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(bmp);
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setColor(color);
        c.drawCircle(lado / 2f, lado / 2f, lado / 2f, p);
        String letra = nombre.trim().length() > 0 ? nombre.trim().substring(0, 1).toUpperCase() : "K";
        p.setColor(Color.WHITE);
        p.setTypeface(Typeface.DEFAULT_BOLD);
        p.setTextSize(lado * 0.5f);
        p.setTextAlign(Paint.Align.CENTER);
        Rect r = new Rect();
        p.getTextBounds(letra, 0, letra.length(), r);
        c.drawText(letra, lado / 2f, lado / 2f + r.height() / 2f, p);
        return bmp;
    }

    public static String abrirHtml(Activity act, String ruta, String nombre) {
        if (Build.VERSION.SDK_INT < 29) {
            return ArchivosKira.guardarEnDescargas(act, ruta, nombre, "text/html") ? "guardado" : "";
        }
        InputStream in = null;
        OutputStream out = null;
        Uri uri = null;
        try {
            ContentValues v = new ContentValues();
            v.put(MediaStore.MediaColumns.DISPLAY_NAME, nombre);
            v.put(MediaStore.MediaColumns.MIME_TYPE, "text/html");
            v.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Kira");
            uri = act.getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v);
            if (uri == null) return "";
            in = new FileInputStream(ruta);
            out = act.getContentResolver().openOutputStream(uri);
            if (out == null) return "";
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        } catch (Throwable t) {
            return "";
        } finally {
            try { if (in != null) in.close(); } catch (Exception e) { }
            try { if (out != null) out.close(); } catch (Exception e) { }
        }
        try {
            Intent ver = new Intent(Intent.ACTION_VIEW);
            ver.setDataAndType(uri, "text/html");
            ver.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            act.startActivity(ver);
            return "abierto";
        } catch (Throwable t) {
            return "guardado";
        }
    }
}
