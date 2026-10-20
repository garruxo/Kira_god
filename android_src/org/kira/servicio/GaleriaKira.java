package org.kira.servicio;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * Guarda en la GALERÍA del móvil (Imágenes/Kira) las imágenes que pinta Kira.
 *   guardar(ctx, ruta, nombre) -> la dirección donde quedó, o "" si Android no lo permitió.
 * Android 10 o más: MediaStore (no necesita permisos). Antes: copia en Pictures/Kira y avisa a la galería.
 */
public class GaleriaKira {

    private static void copiar(InputStream entrada, OutputStream salida) throws Exception {
        byte[] trozo = new byte[65536];
        int n;
        while ((n = entrada.read(trozo)) > 0) {
            salida.write(trozo, 0, n);
        }
        salida.flush();
    }

    public static String guardar(Context ctx, String ruta, String nombre) {
        InputStream entrada = null;
        OutputStream salida = null;
        try {
            entrada = new FileInputStream(new File(ruta));
            if (Build.VERSION.SDK_INT >= 29) {
                ContentResolver cr = ctx.getContentResolver();
                ContentValues v = new ContentValues();
                v.put(MediaStore.Images.Media.DISPLAY_NAME, nombre);
                v.put(MediaStore.Images.Media.MIME_TYPE, "image/png");
                v.put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/Kira");
                v.put(MediaStore.Images.Media.IS_PENDING, 1);
                Uri uri = cr.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, v);
                if (uri == null) {
                    return "";
                }
                salida = cr.openOutputStream(uri);
                if (salida == null) {
                    return "";
                }
                copiar(entrada, salida);
                salida.close();
                salida = null;
                ContentValues fin = new ContentValues();
                fin.put(MediaStore.Images.Media.IS_PENDING, 0);
                cr.update(uri, fin, null, null);
                return uri.toString();
            }
            File carpeta = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES), "Kira");
            if (!carpeta.isDirectory() && !carpeta.mkdirs()) {
                return "";
            }
            File destino = new File(carpeta, nombre);
            salida = new FileOutputStream(destino);
            copiar(entrada, salida);
            salida.close();
            salida = null;
            MediaScannerConnection.scanFile(ctx, new String[]{destino.getAbsolutePath()}, new String[]{"image/png"}, null);
            return destino.getAbsolutePath();
        } catch (Exception e) {
            return "";
        } finally {
            try {
                if (entrada != null) {
                    entrada.close();
                }
            } catch (Exception e) {
                // nada
            }
            try {
                if (salida != null) {
                    salida.close();
                }
            } catch (Exception e) {
                // nada
            }
        }
    }
}
