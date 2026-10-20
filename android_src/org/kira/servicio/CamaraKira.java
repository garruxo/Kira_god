package org.kira.servicio;

import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.ImageFormat;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.TotalCaptureResult;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.Image;
import android.media.ImageReader;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Size;
import android.view.Surface;

import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.util.Arrays;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * Cámara de Kira: hace UNA foto sin abrir ninguna app de cámara (Camera2) y la guarda en un JPEG.
 *   foto(ctx, ruta, trasera, maxLado) -> "" si todo fue bien, o el motivo del fallo.
 * Bloquea hasta 10 s: se llama desde un hilo (nunca desde el de la pantalla).
 * Antes de disparar deja unos fotogramas de «previsualización» invisibles para que la luz y el enfoque se ajusten.
 */
public class CamaraKira {
    private static String error;

    public static boolean tienePermiso(Context ctx) {
        return ctx.checkSelfPermission(android.Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
    }

    public static boolean hayCamara(Context ctx, boolean trasera) {
        try {
            return elegir((CameraManager) ctx.getSystemService(Context.CAMERA_SERVICE), trasera) != null;
        } catch (Exception e) {
            return false;
        }
    }

    private static String elegir(CameraManager m, boolean trasera) throws CameraAccessException {
        String otra = null;
        int quiero = trasera ? CameraCharacteristics.LENS_FACING_BACK : CameraCharacteristics.LENS_FACING_FRONT;
        for (String id : m.getCameraIdList()) {
            Integer lado = m.getCameraCharacteristics(id).get(CameraCharacteristics.LENS_FACING);
            if (lado != null && lado == quiero) return id;
            if (otra == null) otra = id;
        }
        return otra;                                        // si no hay la que pides, cualquiera
    }

    private static Size tamano(Size[] tams, int maxLado) {
        Size mejor = null;
        for (Size s : tams) {
            int lado = Math.max(s.getWidth(), s.getHeight());
            if (lado <= maxLado && (mejor == null || s.getWidth() * s.getHeight() > mejor.getWidth() * mejor.getHeight()))
                mejor = s;
        }
        if (mejor == null) {                                // todas son grandes: la más pequeña
            for (Size s : tams)
                if (mejor == null || s.getWidth() * s.getHeight() < mejor.getWidth() * mejor.getHeight()) mejor = s;
        }
        return mejor;
    }

    public static String foto(Context ctx, final String ruta, boolean trasera, int maxLado) {
        if (!tienePermiso(ctx)) return "sin permiso de cámara";
        error = null;
        final HandlerThread hilo = new HandlerThread("kira-camara");
        hilo.start();
        final Handler h = new Handler(hilo.getLooper());
        final CountDownLatch listo = new CountDownLatch(1);
        final CameraDevice[] dispositivo = new CameraDevice[1];
        final ImageReader[] lectores = new ImageReader[2];
        try {
            CameraManager m = (CameraManager) ctx.getSystemService(Context.CAMERA_SERVICE);
            String id = elegir(m, trasera);
            if (id == null) return "este móvil no tiene cámara";
            CameraCharacteristics c = m.getCameraCharacteristics(id);
            StreamConfigurationMap mapa = c.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
            Size jpg = tamano(mapa.getOutputSizes(ImageFormat.JPEG), maxLado);
            Size prev = tamano(mapa.getOutputSizes(ImageFormat.YUV_420_888), 640);
            Integer giro = c.get(CameraCharacteristics.SENSOR_ORIENTATION);
            final int orientacion = giro == null ? 90 : giro;            // móvil en vertical
            final ImageReader foto = ImageReader.newInstance(jpg.getWidth(), jpg.getHeight(), ImageFormat.JPEG, 1);
            final ImageReader vista = ImageReader.newInstance(prev.getWidth(), prev.getHeight(), ImageFormat.YUV_420_888, 2);
            lectores[0] = foto;
            lectores[1] = vista;
            vista.setOnImageAvailableListener(new ImageReader.OnImageAvailableListener() {
                @Override
                public void onImageAvailable(ImageReader r) {   // fotogramas de ajuste: se tiran
                    Image i = r.acquireLatestImage();
                    if (i != null) i.close();
                }
            }, h);
            foto.setOnImageAvailableListener(new ImageReader.OnImageAvailableListener() {
              @Override
              public void onImageAvailable(ImageReader r) {
                Image i = r.acquireLatestImage();
                if (i == null) return;
                try {
                    ByteBuffer b = i.getPlanes()[0].getBuffer();
                    byte[] datos = new byte[b.remaining()];
                    b.get(datos);
                    FileOutputStream out = new FileOutputStream(ruta);
                    out.write(datos);
                    out.close();
                } catch (Exception e) {
                    error = "no pude guardar la foto: " + e;
                } finally {
                    i.close();
                    listo.countDown();
                }
              }
            }, h);
            m.openCamera(id, new CameraDevice.StateCallback() {
                @Override
                public void onOpened(final CameraDevice cam) {
                    dispositivo[0] = cam;
                    try {
                        cam.createCaptureSession(Arrays.asList(vista.getSurface(), foto.getSurface()),
                                new CameraCaptureSession.StateCallback() {
                                    @Override
                                    public void onConfigured(final CameraCaptureSession s) {
                                        try {
                                            CaptureRequest.Builder pr = cam.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
                                            pr.addTarget(vista.getSurface());
                                            pr.set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO);
                                            pr.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
                                            s.setRepeatingRequest(pr.build(), null, h);
                                            h.postDelayed(new Runnable() {
                                                @Override
                                                public void run() {
                                                    disparar(cam, s, foto.getSurface(), orientacion, h, listo);
                                                }
                                            }, 1200);
                                        } catch (Exception e) {
                                            error = "no pude preparar la cámara: " + e;
                                            listo.countDown();
                                        }
                                    }

                                    @Override
                                    public void onConfigureFailed(CameraCaptureSession s) {
                                        error = "la cámara no aceptó la configuración";
                                        listo.countDown();
                                    }
                                }, h);
                    } catch (Exception e) {
                        error = "no pude usar la cámara: " + e;
                        listo.countDown();
                    }
                }

                @Override
                public void onDisconnected(CameraDevice cam) {
                    cam.close();
                    if (error == null) error = "otra app está usando la cámara";
                    listo.countDown();
                }

                @Override
                public void onError(CameraDevice cam, int codigo) {
                    cam.close();
                    error = "error de cámara " + codigo + (codigo == 1 || codigo == 2 ? " (otra app la está usando)" : "");
                    listo.countDown();
                }
            }, h);
            if (!listo.await(10, TimeUnit.SECONDS) && error == null) error = "la cámara tardó demasiado";
        } catch (SecurityException e) {
            error = "sin permiso de cámara";
        } catch (Exception e) {
            error = "no pude abrir la cámara: " + e;
        } finally {
            try { if (dispositivo[0] != null) dispositivo[0].close(); } catch (Exception e) { }
            for (ImageReader r : lectores) {
                try { if (r != null) r.close(); } catch (Exception e) { }
            }
            hilo.quitSafely();
        }
        return error == null ? "" : error;
    }

    private static void disparar(CameraDevice cam, CameraCaptureSession s, Surface destino, int orientacion, Handler h,
                                 final CountDownLatch listo) {
        try {
            CaptureRequest.Builder b = cam.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE);
            b.addTarget(destino);
            b.set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO);
            b.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
            b.set(CaptureRequest.JPEG_ORIENTATION, orientacion);
            b.set(CaptureRequest.JPEG_QUALITY, (byte) 90);
            s.capture(b.build(), new CameraCaptureSession.CaptureCallback() {
                @Override
                public void onCaptureFailed(CameraCaptureSession ss, CaptureRequest r, android.hardware.camera2.CaptureFailure f) {
                    error = "la foto falló";
                    listo.countDown();
                }
            }, h);
        } catch (Exception e) {
            error = "no pude hacer la foto: " + e;
            listo.countDown();
        }
    }
}
