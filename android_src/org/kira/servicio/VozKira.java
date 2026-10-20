package org.kira.servicio;

import android.content.Context;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;

import java.util.Locale;

/**
 * La VOZ de Kira: un solo motor de texto a voz, creado UNA vez y en ESPAÑOL.
 * (La librería plyer creaba un motor nuevo en cada frase y lo ponía en inglés: tardaba segundos en empezar.)
 *   iniciar(ctx)              lo prepara (no bloquea; tarda un momento la primera vez)
 *   hablar(texto, encolar)    encolar=true: se dice DETRÁS de lo que ya está diciendo (frase a frase)
 *   hablando()                ¿está diciendo algo o le queda algo en cola?
 *   callar(), velocidad(v), lista(), error()
 */
public class VozKira {
    private static TextToSpeech tts = null;
    private static volatile boolean lista = false;
    private static volatile String error = "";
    private static volatile String ultimo = "";     // id de la última frase pedida
    private static volatile boolean acabada = true;  // ¿ya terminó (o se cortó) esa última frase?
    private static float velocidad = 1.05f;
    private static int contador = 0;

    public static synchronized void iniciar(Context ctx) {
        if (tts != null) {
            return;
        }
        final Context app = ctx.getApplicationContext();
        tts = new TextToSpeech(app, new TextToSpeech.OnInitListener() {
            @Override
            public void onInit(int estado) {
                if (estado != TextToSpeech.SUCCESS) {
                    error = "el motor de voz no arrancó (" + estado + ")";
                    return;
                }
                int r = tts.setLanguage(new Locale("es", "ES"));
                if (r == TextToSpeech.LANG_MISSING_DATA || r == TextToSpeech.LANG_NOT_SUPPORTED) {
                    r = tts.setLanguage(new Locale("es"));
                    if (r == TextToSpeech.LANG_MISSING_DATA || r == TextToSpeech.LANG_NOT_SUPPORTED) {
                        error = "no hay voz en español instalada (Ajustes > Texto a voz)";
                    }
                }
                tts.setSpeechRate(velocidad);
                tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                    @Override
                    public void onStart(String id) {
                    }

                    @Override
                    public void onDone(String id) {
                        fin(id);
                    }

                    @Override
                    public void onError(String id) {
                        fin(id);
                    }

                    @Override
                    public void onStop(String id, boolean interrumpido) {
                        fin(id);
                    }
                });
                lista = true;
            }
        });
    }

    private static void fin(String id) {
        if (id != null && id.equals(ultimo)) {   // solo cuenta la ÚLTIMA: las cortadas por una nueva no
            acabada = true;
        }
    }

    public static boolean lista() {
        return lista;
    }

    public static String error() {
        return error;
    }

    public static synchronized boolean hablar(String texto, boolean encolar) {
        if (tts == null || !lista || texto == null || texto.length() == 0) {
            return false;
        }
        contador++;
        String id = "kira" + contador;
        ultimo = id;
        acabada = false;
        int r = tts.speak(texto, encolar ? TextToSpeech.QUEUE_ADD : TextToSpeech.QUEUE_FLUSH, new Bundle(), id);
        if (r != TextToSpeech.SUCCESS) {
            acabada = true;
            return false;
        }
        return true;
    }

    public static boolean hablando() {
        TextToSpeech t = tts;
        return t != null && (!acabada || t.isSpeaking());
    }

    public static synchronized void callar() {
        if (tts != null) {
            tts.stop();
        }
        acabada = true;
    }

    public static synchronized void velocidad(float v) {
        velocidad = v;
        if (tts != null && lista) {
            tts.setSpeechRate(v);
        }
    }

    public static synchronized void apagar() {
        if (tts != null) {
            tts.shutdown();
        }
        tts = null;
        lista = false;
        acabada = true;
    }
}
