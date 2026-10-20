package org.kira.servicio;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.app.usage.UsageEvents;
import android.app.usage.UsageStatsManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.graphics.Bitmap;
import android.graphics.PixelFormat;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.PowerManager;
import android.net.Uri;
import android.provider.Settings;
import android.util.DisplayMetrics;
import android.view.WindowManager;

import java.io.FileOutputStream;
import java.nio.ByteBuffer;

/**
 * Servicio en primer plano de Kira: la mantiene ACTIVA (con su notificación) para que pueda seguir oyendo
 * mientras usas otras apps y, si tú lo permites, VER LA PANTALLA cuando se lo pidas.
 *
 *  - iniciar(ctx, false)                 -> solo «Kira activa» (micrófono).
 *  - iniciarPantalla(ctx, codigo, datos) -> además guarda el permiso de captura que Android te ha pedido.
 *  - capturar(ruta)                      -> guarda la pantalla actual en un PNG (true si pudo).
 *  - appEnPrimerPlano(ctx)               -> paquete de la app que tienes delante (necesita «Acceso a datos de uso»).
 *  - detener(ctx)                        -> quita la notificación, suelta la captura y para el servicio.
 * Nada sale del móvil: la captura se guarda en la carpeta privada de Kira y se lee allí mismo.
 */
public class ServicioKira extends Service {
    private static final String CANAL = "kira_activa";
    private static final int ID = 4711;
    private static ServicioKira instancia;
    private static MediaProjection proyeccion;
    private static VirtualDisplay pantallaVirtual;
    private static ImageReader lector;
    private static HandlerThread hilo;
    private static int ancho, alto;

    // ---------------- control desde Python ----------------
    public static void iniciar(Context ctx, boolean conPantalla) {
        Intent i = new Intent(ctx, ServicioKira.class);
        i.putExtra("pantalla", conPantalla);
        if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(i); else ctx.startService(i);
    }

    public static void iniciarPantalla(Context ctx, int codigo, Intent datos) {
        Intent i = new Intent(ctx, ServicioKira.class);
        i.putExtra("pantalla", true);
        i.putExtra("codigo", codigo);
        i.putExtra("datos", datos);
        if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(i); else ctx.startService(i);
    }

    public static void detener(Context ctx) {
        soltarPantalla();
        ctx.stopService(new Intent(ctx, ServicioKira.class));
    }

    /** ¿Android deja a Kira fuera del «ahorro de batería»? (si no, al apagar la pantalla puede cerrarla) */
    public static boolean sinAhorro(Context ctx) {
        try {
            if (Build.VERSION.SDK_INT < 23) return true;
            PowerManager pm = (PowerManager) ctx.getSystemService(Context.POWER_SERVICE);
            return pm != null && pm.isIgnoringBatteryOptimizations(ctx.getPackageName());
        } catch (Throwable t) {
            return false;
        }
    }

    /** Pide a Android (una ventana suya) que no duerma a Kira. true si ya lo estaba. */
    public static boolean pedirSinAhorro(Context ctx) {
        if (sinAhorro(ctx)) return true;
        try {
            Intent i = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                    Uri.parse("package:" + ctx.getPackageName()));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            ctx.startActivity(i);
        } catch (Throwable t) {
            try {
                Intent j = new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS);
                j.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                ctx.startActivity(j);
            } catch (Throwable t2) {
                // nada: el usuario puede hacerlo a mano en Ajustes › Batería
            }
        }
        return false;
    }

    public static boolean activo() {
        return instancia != null;
    }

    public static boolean puedeVer() {
        return proyeccion != null && lector != null;
    }

    public static Intent pedirPermisoPantalla(Context ctx) {
        MediaProjectionManager m = (MediaProjectionManager) ctx.getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        return m.createScreenCaptureIntent();
    }

    // ---------------- servicio ----------------
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        instancia = this;
        boolean conPantalla = intent != null && intent.getBooleanExtra("pantalla", false);
        Intent datos = intent != null ? (Intent) intent.getParcelableExtra("datos") : null;
        boolean ver = conPantalla && datos != null;
        Notification n = notificacion(ver ? "Kira está activa y puede ver la pantalla" : "Kira está activa y te escucha");
        if (Build.VERSION.SDK_INT >= 29) {
            int tipo = ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE;
            if (ver) tipo |= ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION;
            startForeground(ID, n, tipo);
        } else {
            startForeground(ID, n);
        }
        if (ver) {
            prepararPantalla(intent.getIntExtra("codigo", 0), datos);   // después de startForeground (Android 14)
        }
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        soltarPantalla();
        instancia = null;
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private Notification notificacion(String texto) {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel c = new NotificationChannel(CANAL, "Kira activa", NotificationManager.IMPORTANCE_LOW);
            c.setDescription("Aviso fijo mientras Kira está activa");
            nm.createNotificationChannel(c);
        }
        Intent abrir = getPackageManager().getLaunchIntentForPackage(getPackageName());
        PendingIntent pi = abrir == null ? null : PendingIntent.getActivity(this, 0, abrir,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b = Build.VERSION.SDK_INT >= 26 ? new Notification.Builder(this, CANAL)
                : new Notification.Builder(this);
        b.setContentTitle("Kira").setContentText(texto).setSmallIcon(getApplicationInfo().icon).setOngoing(true);
        if (pi != null) b.setContentIntent(pi);
        return b.build();
    }

    // ---------------- ver la pantalla ----------------
    private void prepararPantalla(int codigo, Intent datos) {
        soltarPantalla();
        MediaProjectionManager m = (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        proyeccion = m.getMediaProjection(codigo, datos);
        if (proyeccion == null) return;
        hilo = new HandlerThread("kira-pantalla");
        hilo.start();
        Handler h = new Handler(hilo.getLooper());
        proyeccion.registerCallback(new MediaProjection.Callback() {
            @Override
            public void onStop() {           // tú quitaste el permiso (o Android lo cerró)
                soltarPantalla();
            }
        }, h);
        DisplayMetrics dm = new DisplayMetrics();
        ((WindowManager) getSystemService(Context.WINDOW_SERVICE)).getDefaultDisplay().getRealMetrics(dm);
        float escala = Math.min(1f, 1280f / Math.max(dm.widthPixels, dm.heightPixels));   // basta para leer texto
        ancho = Math.max(1, Math.round(dm.widthPixels * escala));
        alto = Math.max(1, Math.round(dm.heightPixels * escala));
        lector = ImageReader.newInstance(ancho, alto, PixelFormat.RGBA_8888, 2);
        pantallaVirtual = proyeccion.createVirtualDisplay("kira-pantalla", ancho, alto, dm.densityDpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR, lector.getSurface(), null, h);
    }

    private static void soltarPantalla() {
        try { if (pantallaVirtual != null) pantallaVirtual.release(); } catch (Exception e) { }
        try { if (lector != null) lector.close(); } catch (Exception e) { }
        try { if (proyeccion != null) proyeccion.stop(); } catch (Exception e) { }
        try { if (hilo != null) hilo.quitSafely(); } catch (Exception e) { }
        pantallaVirtual = null;
        lector = null;
        proyeccion = null;
        hilo = null;
    }

    public static boolean capturar(String ruta) {
        if (lector == null) return false;
        Image img = null;
        for (int intento = 0; intento < 20 && img == null; intento++) {      // hasta 2 s esperando un fotograma
            img = lector.acquireLatestImage();
            if (img == null) {
                try { Thread.sleep(100); } catch (InterruptedException e) { return false; }
            }
        }
        if (img == null) return false;
        try {
            Image.Plane plano = img.getPlanes()[0];
            ByteBuffer buf = plano.getBuffer();
            int paso = plano.getPixelStride();
            int fila = plano.getRowStride();
            int relleno = fila - paso * ancho;
            Bitmap bmp = Bitmap.createBitmap(ancho + relleno / paso, alto, Bitmap.Config.ARGB_8888);
            bmp.copyPixelsFromBuffer(buf);
            Bitmap recorte = Bitmap.createBitmap(bmp, 0, 0, ancho, alto);
            FileOutputStream out = new FileOutputStream(ruta);
            recorte.compress(Bitmap.CompressFormat.PNG, 100, out);
            out.close();
            bmp.recycle();
            recorte.recycle();
            return true;
        } catch (Exception e) {
            return false;
        } finally {
            img.close();
        }
    }

    // ---------------- qué app tienes delante ----------------
    public static String appEnPrimerPlano(Context ctx) {
        try {
            UsageStatsManager u = (UsageStatsManager) ctx.getSystemService(Context.USAGE_STATS_SERVICE);
            long ahora = System.currentTimeMillis();
            UsageEvents ev = u.queryEvents(ahora - 10 * 60 * 1000, ahora);
            UsageEvents.Event e = new UsageEvents.Event();
            String ultima = null;
            while (ev.hasNextEvent()) {
                ev.getNextEvent(e);
                if (e.getEventType() == UsageEvents.Event.MOVE_TO_FOREGROUND) ultima = e.getPackageName();
            }
            return ultima;
        } catch (Exception ex) {
            return null;
        }
    }

    public static boolean tieneAccesoUso(Context ctx) {
        try {
            android.app.AppOpsManager ops = (android.app.AppOpsManager) ctx.getSystemService(Context.APP_OPS_SERVICE);
            int modo = ops.checkOpNoThrow(android.app.AppOpsManager.OPSTR_GET_USAGE_STATS,
                    android.os.Process.myUid(), ctx.getPackageName());
            return modo == android.app.AppOpsManager.MODE_ALLOWED;
        } catch (Exception e) {
            return false;
        }
    }
}
