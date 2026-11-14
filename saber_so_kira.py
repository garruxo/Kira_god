# -*- coding: utf-8 -*-
"""
saber_so_kira.py — v3.35: SISTEMAS OPERATIVOS POR DENTRO (cómo se programa un kernel), para Kira.

Lo pidió el dueño: que Kira sepa programar un sistema operativo desde cero. Aquí hay dos cosas, escritas y revisadas a
mano (no vienen de internet):

  CONCEPTOS  : fichas de teoría (arranque, Multiboot, modo protegido, GDT, IDT, PIC, PIT, teclado, puerto serie,
               memoria física, paginación, heap, multitarea, modo usuario y llamadas al sistema, sistema de archivos,
               depurar un triple fault). «estudia sistemas operativos por dentro» las guarda en el baúl.
  ETAPAS     : PLANTILLAS de kernel x86 de 32 bits en C freestanding + NASM, por etapas, cada una con TODOS sus archivos
               (acumulativas) y la marca que debe salir por el puerto serie si funciona. Las usa el TALLER DE KERNEL
               de KiraOS (kira_portatil/taller_kernel_kira.py): con el cerebro pequeño, Kira ADAPTA código que ya
               funciona en vez de inventarlo. El flujo .github/workflows/probar_kernel.yml las compila y las arranca
               de verdad en QEMU.

Puro: sin red, sin Kivy, sin ejecutar nada. Va también en el APK (el móvil puede estudiar las fichas).
"""
import re
import unicodedata

FUENTE = "saber propio: sistemas operativos por dentro"

# ---------------------------------------------------------------- fichas de teoría
CONCEPTOS = [
("arranque de un ordenador (BIOS, UEFI y bootloader)",
 "Al encender, el procesador empieza en modo real de 16 bits y ejecuta el firmware (BIOS o UEFI). El firmware busca un "
 "disco arrancable y carga el BOOTLOADER (GRUB, Limine…), que a su vez carga el kernel en memoria y le salta. Escribir "
 "tu propio bootloader es posible pero lento; lo normal al empezar es usar GRUB o el cargador Multiboot de QEMU "
 "(qemu-system-i386 -kernel kernel.bin) y dedicarse al kernel."),
("Multiboot",
 "Multiboot es un acuerdo entre bootloader y kernel: el kernel lleva al principio una cabecera con el número mágico "
 "0x1BADB002, unas banderas y una suma de control (magic + flags + checksum = 0). El cargador deja el procesador en "
 "modo protegido de 32 bits, pone en EAX 0x2BADB002 y en EBX la dirección de una estructura con la memoria disponible "
 "(mem_lower, mem_upper, mapa de memoria) y los módulos cargados. La cabecera debe estar en los primeros 8 KB del "
 "archivo: por eso el linker script pone la sección .multiboot la primera."),
("kernel freestanding (C sin biblioteca estándar)",
 "Un kernel no tiene libc debajo: no hay printf, malloc ni archivos. Se compila con gcc -ffreestanding -nostdlib "
 "-fno-stack-protector -fno-pic (y -m32 para 32 bits). Solo se pueden usar las cabeceras que da el propio compilador "
 "(stdint.h, stddef.h, stdbool.h, stdarg.h). Todo lo demás —escribir en pantalla, reservar memoria— lo programa el "
 "kernel. El punto de entrada es un _start en ensamblador que pone una pila y llama a kernel_main."),
("linker script de un kernel",
 "El linker script (linker.ld) dice dónde se coloca cada sección: ENTRY(_start), el kernel a partir de 1 MB "
 "(. = 1M), primero .multiboot y .text, luego .rodata, .data y .bss alineadas a 4 KB. Se puede añadir un símbolo al "
 "final (fin_kernel = .;) para saber dónde acaba el kernel y empezar a repartir la memoria libre desde ahí."),
("pantalla VGA en modo texto y puerto serie",
 "En modo texto la pantalla es una tabla de 80x25 celdas en la dirección 0xB8000: cada celda son 2 bytes (el carácter "
 "y el color). El puerto serie COM1 (puerto de E/S 0x3F8) sirve para depurar: se configura (velocidad, 8N1, FIFO) y se "
 "escribe un byte cuando el bit 5 del registro de estado (0x3F8+5) dice que está libre. QEMU con -serial stdio saca "
 "ese texto por la terminal: así se comprueba un kernel sin mirar la pantalla."),
("puertos de entrada/salida (inb y outb)",
 "Muchos aparatos del PC (teclado, PIC, PIT, puerto serie) se manejan con instrucciones especiales de E/S: outb "
 "escribe un byte en un puerto y inb lo lee. En C se hacen con ensamblador en línea: "
 "__asm__ volatile(\"outb %0, %1\" : : \"a\"(valor), \"Nd\"(puerto)). io_wait (escribir en el puerto 0x80) da un "
 "respiro a los aparatos viejos."),
("modo protegido y la GDT",
 "En modo protegido la memoria se accede a través de SEGMENTOS descritos en la GDT (Global Descriptor Table). Cada "
 "entrada de 8 bytes guarda base, límite, permisos (byte de acceso: 0x9A código del kernel, 0x92 datos del kernel, "
 "0xFA/0xF2 los de usuario) y granularidad (0xCF = 4 KB y 32 bits). Lo habitual es el MODELO PLANO: base 0 y límite "
 "4 GB, y la protección de verdad se hace con la paginación. Se carga con lgdt y después hay que recargar los "
 "registros de segmento (ds, es, fs, gs, ss = 0x10) y CS con un salto lejano (jmp 0x08:etiqueta)."),
("interrupciones y la IDT",
 "La IDT (Interrupt Descriptor Table) tiene 256 entradas; cada una dice qué función atiende esa interrupción "
 "(dirección, selector de código 0x08 y tipo 0x8E = puerta de interrupción de 32 bits del kernel). Las 32 primeras "
 "son EXCEPCIONES del procesador (0 división por cero, 6 instrucción inválida, 8 doble fallo, 13 protección general, "
 "14 fallo de página…); algunas meten un código de error en la pila (8, 10-14, 17, 21, 29, 30). Cada entrada apunta a "
 "un trocito en ensamblador que guarda los registros (pusha, segmentos), llama a un manejador en C y vuelve con iret."),
("PIC 8259 y las IRQ",
 "Los aparatos avisan con IRQ a través del PIC 8259 (dos en cascada: maestro 0x20/0x21 y esclavo 0xA0/0xA1). Por "
 "defecto las IRQ 0-7 caen en las interrupciones 8-15, que chocan con las excepciones; por eso se REMAPEAN a 32-47 "
 "con la secuencia ICW1-ICW4. Al terminar de atender una IRQ hay que mandar EOI (0x20) al PIC (y también al esclavo "
 "si la IRQ es 8 o más). Con la máscara (0x21/0xA1) se eligen qué IRQ se escuchan."),
("temporizador PIT",
 "El PIT 8254 cuenta a 1 193 182 Hz. Programando el canal 0 (orden 0x36 al puerto 0x43 y el divisor en dos bytes al "
 "puerto 0x40) dispara la IRQ 0 a la frecuencia que quieras (divisor = 1193182 / hercios; 100 Hz es típico). Cada "
 "tic sirve para llevar la hora del sistema y, más adelante, para que el planificador reparta el procesador."),
("teclado PS/2",
 "El teclado avisa con la IRQ 1; el código de la tecla (scancode, juego 1) se lee del puerto 0x60. Si el bit 7 está "
 "a 1 es que se ha SOLTADO la tecla. Una tabla traduce scancodes a letras; hay que llevar el estado de mayúsculas, "
 "control y alt. Con QEMU sin pantalla no se puede teclear, por eso las pruebas automáticas usan el temporizador."),
("memoria física (marcos y mapa de bits)",
 "La memoria se reparte en MARCOS de 4 KB. Un mapa de bits (un bit por marco) dice cuáles están ocupados. Al arrancar "
 "se marca todo como ocupado y se liberan las zonas que Multiboot dice que están libres, menos las que ocupa el propio "
 "kernel (hasta fin_kernel). reservar_marco busca el primer bit a 0; liberar_marco lo vuelve a poner a 0."),
("paginación",
 "Con la paginación cada dirección virtual se traduce a física con dos niveles de tablas: el DIRECTORIO de páginas "
 "(1024 entradas) apunta a TABLAS de páginas (1024 entradas de 4 KB cada una = 4 MB por tabla). Cada entrada lleva la "
 "dirección del marco y banderas (bit 0 presente, bit 1 escritura, bit 2 usuario). Se activa cargando el directorio "
 "en CR3 y poniendo el bit 31 de CR0. Lo primero es un MAPA IDENTIDAD (virtual = física) de lo que ocupa el kernel; "
 "si se toca una página no mapeada salta la excepción 14 y CR2 dice qué dirección fue."),
("heap del kernel (kmalloc)",
 "Encima de los marcos se construye un montón para pedir trozos pequeños: kmalloc(tamaño) y kfree(puntero). Lo más "
 "simple es un puntero que avanza (no libera nunca); lo siguiente, una lista de bloques libres con cabecera "
 "(tamaño + libre) que se parten y se juntan. Alinear a 8 o 16 bytes evita sorpresas."),
("multitarea y cambio de contexto",
 "Cada tarea tiene su pila y su estado guardado (registros, EIP, ESP, su directorio de páginas). El CAMBIO DE "
 "CONTEXTO guarda los registros de la tarea actual en su estructura, carga los de la siguiente y salta a ella. El "
 "planificador elige cuál toca: el más simple es turno rotatorio (round robin) disparado por el temporizador. Hay que "
 "proteger las estructuras compartidas (desactivar interrupciones un momento o usar cerrojos)."),
("modo usuario, TSS y llamadas al sistema",
 "Los programas corren en el anillo 3 (sin permisos) y el kernel en el anillo 0. Para pasar a usuario se preparan "
 "segmentos de usuario en la GDT y se hace iret con CS/SS de usuario. Para volver al kernel cuando ocurre una "
 "interrupción, la TSS guarda la pila del kernel (esp0). Las LLAMADAS AL SISTEMA (syscalls) son una interrupción "
 "acordada (Linux usaba int 0x80) con el número de la llamada en EAX y los argumentos en otros registros."),
("sistema de archivos e initrd",
 "Antes de tener drivers de disco, lo cómodo es un INITRD: un archivo (por ejemplo un tar) que el bootloader carga en "
 "memoria como módulo Multiboot y que el kernel lee como si fuera un disco. Después se programa un driver (ATA/AHCI) "
 "y un sistema de archivos sencillo (FAT32 o ext2), con una capa VFS que unifica abrir/leer/escribir."),
("depurar un kernel con QEMU (triple fault)",
 "Si el kernel falla dentro de un manejador de excepciones salta el DOBLE fallo y, si ese también falla, el TRIPLE "
 "fallo: el procesador se reinicia sin decir nada. Para verlo: qemu-system-i386 -kernel kernel.bin -serial stdio "
 "-no-reboot -d int,cpu_reset -D qemu.log. En el registro se busca la última línea «v=XX»: v=0d protección general "
 "(segmento o selector malo, casi siempre la GDT/IDT), v=0e fallo de página (mirar CR2), v=08 doble fallo, v=06 "
 "instrucción inválida. Imprimir por el puerto serie en cada paso ayuda a saber dónde se para."),
]


def fichas():
    """[(tema, texto)] para guardar en el baúl (estudio_kira)."""
    return [(t, x) for t, x in CONCEPTOS]


# ---------------------------------------------------------------- plantillas (etapas)
_BOOT = r"""; boot.s — punto de entrada Multiboot (QEMU lo carga con -kernel; GRUB también)
MBALIGN  equ 1 << 0
MEMINFO  equ 1 << 1
FLAGS    equ MBALIGN | MEMINFO
MAGIC    equ 0x1BADB002
CHECKSUM equ -(MAGIC + FLAGS)

section .multiboot
align 4
    dd MAGIC
    dd FLAGS
    dd CHECKSUM

section .bss
align 16
pila_fondo:
    resb 16384              ; 16 KiB de pila
pila_cima:

section .text
global _start
extern kernel_main
_start:
    mov esp, pila_cima
    push ebx                ; puntero a la información de Multiboot
    push eax                ; número mágico
    call kernel_main
    cli
.parado:
    hlt
    jmp .parado
"""

_LINKER = r"""ENTRY(_start)

SECTIONS
{
    . = 1M;
    .text BLOCK(4K) : ALIGN(4K)
    {
        *(.multiboot)
        *(.text)
    }
    .rodata BLOCK(4K) : ALIGN(4K) { *(.rodata*) }
    .data   BLOCK(4K) : ALIGN(4K) { *(.data) }
    .bss    BLOCK(4K) : ALIGN(4K)
    {
        *(COMMON)
        *(.bss)
    }
    fin_kernel = .;
}
"""

_IO_H = r"""/* io.h — puertos de entrada/salida */
#ifndef IO_H
#define IO_H
#include <stdint.h>

static inline void outb(uint16_t puerto, uint8_t valor) {
    __asm__ volatile ("outb %0, %1" : : "a"(valor), "Nd"(puerto));
}
static inline uint8_t inb(uint16_t puerto) {
    uint8_t r;
    __asm__ volatile ("inb %1, %0" : "=a"(r) : "Nd"(puerto));
    return r;
}
static inline void outw(uint16_t puerto, uint16_t valor) {
    __asm__ volatile ("outw %0, %1" : : "a"(valor), "Nd"(puerto));
}
static inline uint16_t inw(uint16_t puerto) {
    uint16_t r;
    __asm__ volatile ("inw %1, %0" : "=a"(r) : "Nd"(puerto));
    return r;
}
static inline void outl(uint16_t puerto, uint32_t valor) {
    __asm__ volatile ("outl %0, %1" : : "a"(valor), "Nd"(puerto));
}
static inline uint32_t inl(uint16_t puerto) {
    uint32_t r;
    __asm__ volatile ("inl %1, %0" : "=a"(r) : "Nd"(puerto));
    return r;
}
static inline void io_wait(void) { outb(0x80, 0); }

#endif
"""

_CONSOLA_H = r"""/* consola.h — escribir en pantalla (VGA) y en el puerto serie a la vez */
#ifndef CONSOLA_H
#define CONSOLA_H
#include <stdint.h>

void consola_init(void);
void kputc(char c);
void kprint(const char *s);
void kprint_dec(uint32_t n);
void kprint_hex(uint32_t n);

#endif
"""

_CONSOLA_C = r"""/* consola.c — pantalla VGA de texto + puerto serie COM1 (lo que lee el taller para saber si funciona) */
#include <stddef.h>
#include "consola.h"
#include "io.h"

#define COM1 0x3F8
static volatile uint16_t *const VGA = (uint16_t *)0xB8000;
static size_t fila = 0, col = 0;
static const uint8_t COLOR = 0x0F;            /* blanco sobre negro */

static int serie_ok = 0;                      /* en un portátil de verdad puede no haber puerto serie */

static void serie_init(void) {
    outb(COM1 + 7, 0xAE);    /* registro de prueba: si no devuelve lo escrito, no hay puerto serie */
    if (inb(COM1 + 7) != 0xAE) { serie_ok = 0; return; }
    serie_ok = 1;
    outb(COM1 + 1, 0x00);    /* sin interrupciones */
    outb(COM1 + 3, 0x80);    /* DLAB para poner la velocidad */
    outb(COM1 + 0, 0x03);    /* 38400 baudios */
    outb(COM1 + 1, 0x00);
    outb(COM1 + 3, 0x03);    /* 8 bits, sin paridad, 1 de parada */
    outb(COM1 + 2, 0xC7);    /* FIFO */
    outb(COM1 + 4, 0x0B);
}

static void serie_putc(char c) {
    if (!serie_ok) return;
    for (int i = 0; i < 100000 && (inb(COM1 + 5) & 0x20) == 0; i++) { }   /* nunca esperar para siempre */
    outb(COM1, (uint8_t)c);
}

static void vga_bajar(void) {
    for (size_t i = 0; i < 80 * 24; i++) VGA[i] = VGA[i + 80];
    for (size_t i = 80 * 24; i < 80 * 25; i++) VGA[i] = (uint16_t)' ' | (uint16_t)COLOR << 8;
    fila = 24;
}

static void vga_putc(char c) {
    if (c == '\n') { col = 0; if (++fila == 25) vga_bajar(); return; }
    VGA[fila * 80 + col] = (uint16_t)(uint8_t)c | (uint16_t)COLOR << 8;
    if (++col == 80) { col = 0; if (++fila == 25) vga_bajar(); }
}

void consola_init(void) {
    serie_init();
    for (size_t i = 0; i < 80 * 25; i++) VGA[i] = (uint16_t)' ' | (uint16_t)COLOR << 8;
    fila = col = 0;
}

void kputc(char c) { vga_putc(c); serie_putc(c); }

void kprint(const char *s) { while (*s) kputc(*s++); }

void kprint_dec(uint32_t n) {
    char b[11]; int i = 0;
    if (n == 0) { kputc('0'); return; }
    while (n) { b[i++] = (char)('0' + n % 10); n /= 10; }
    while (i) kputc(b[--i]);
}

void kprint_hex(uint32_t n) {
    const char *d = "0123456789ABCDEF";
    kprint("0x");
    for (int s = 28; s >= 0; s -= 4) kputc(d[(n >> s) & 0xF]);
}
"""

_GDT_C = r"""/* gdt.c — Global Descriptor Table en modelo plano (código y datos del kernel, base 0, límite 4 GB) */
#include <stdint.h>
#include "consola.h"

struct gdt_entrada {
    uint16_t limite_bajo;
    uint16_t base_baja;
    uint8_t  base_media;
    uint8_t  acceso;
    uint8_t  granularidad;
    uint8_t  base_alta;
} __attribute__((packed));

struct gdt_puntero {
    uint16_t limite;
    uint32_t base;
} __attribute__((packed));

static struct gdt_entrada gdt[3];
static struct gdt_puntero gdtp;

extern void gdt_cargar(uint32_t puntero);     /* gdt_asm.s */

static void gdt_poner(int i, uint32_t base, uint32_t limite, uint8_t acceso, uint8_t gran) {
    gdt[i].base_baja    = base & 0xFFFF;
    gdt[i].base_media   = (base >> 16) & 0xFF;
    gdt[i].base_alta    = (base >> 24) & 0xFF;
    gdt[i].limite_bajo  = limite & 0xFFFF;
    gdt[i].granularidad = (uint8_t)(((limite >> 16) & 0x0F) | (gran & 0xF0));
    gdt[i].acceso       = acceso;
}

void gdt_init(void) {
    gdtp.limite = sizeof(gdt) - 1;
    gdtp.base   = (uint32_t)&gdt;
    gdt_poner(0, 0, 0, 0, 0);                    /* descriptor nulo (obligatorio) */
    gdt_poner(1, 0, 0xFFFFFFFF, 0x9A, 0xCF);     /* 0x08: código del kernel */
    gdt_poner(2, 0, 0xFFFFFFFF, 0x92, 0xCF);     /* 0x10: datos del kernel */
    gdt_cargar((uint32_t)&gdtp);
    kprint("GDT OK\n");
}
"""

_GDT_S = r"""; gdt_asm.s — carga la GDT y recarga los registros de segmento
global gdt_cargar
gdt_cargar:
    mov eax, [esp + 4]
    lgdt [eax]
    mov ax, 0x10            ; selector de datos del kernel
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    jmp 0x08:.recarga       ; salto lejano: recarga CS con el selector de código
.recarga:
    ret
"""

_IDT_H = r"""/* idt.h — interrupciones */
#ifndef IDT_H
#define IDT_H
#include <stdint.h>

struct registros {
    uint32_t gs, fs, es, ds;
    uint32_t edi, esi, ebp, esp, ebx, edx, ecx, eax;   /* pusha */
    uint32_t num, err;                                 /* los mete el trocito de isr.s */
    uint32_t eip, cs, eflags;                          /* los mete el procesador */
};

typedef void (*manejador_t)(struct registros *r);

void idt_init(void);
void idt_poner_manejador(int n, manejador_t m);
void irq_fin(int irq);          /* débil aquí; pic.c pone la de verdad */

#endif
"""

_IDT_C = r"""/* idt.c — Interrupt Descriptor Table: 32 excepciones + 16 IRQ (48 entradas) */
#include "idt.h"
#include "consola.h"

struct idt_entrada {
    uint16_t base_baja;
    uint16_t selector;
    uint8_t  cero;
    uint8_t  tipo;
    uint16_t base_alta;
} __attribute__((packed));

struct idt_puntero {
    uint16_t limite;
    uint32_t base;
} __attribute__((packed));

static struct idt_entrada idt[256];
static struct idt_puntero idtp;
static manejador_t manejadores[256];
extern uint32_t isr_tabla[];                 /* isr.s: direcciones de isr0..isr47 */

static const char *NOMBRES[32] = {
    "division por cero", "depuracion", "NMI", "punto de ruptura", "desbordamiento", "fuera de rango",
    "instruccion invalida", "sin coprocesador", "doble fallo", "segmento del coprocesador", "TSS invalida",
    "segmento no presente", "fallo de pila", "proteccion general", "fallo de pagina", "reservada",
    "error de coma flotante", "alineacion", "comprobacion de maquina", "SIMD", "virtualizacion", "proteccion de control",
    "reservada", "reservada", "reservada", "reservada", "reservada", "reservada", "hipervisor", "VMM", "seguridad",
    "reservada"
};

void __attribute__((weak)) irq_fin(int irq) { (void)irq; }

void idt_poner_manejador(int n, manejador_t m) {
    if (n >= 0 && n < 256) manejadores[n] = m;
}

static void idt_poner(int n, uint32_t base, uint16_t sel, uint8_t tipo) {
    idt[n].base_baja = base & 0xFFFF;
    idt[n].base_alta = (base >> 16) & 0xFFFF;
    idt[n].selector  = sel;
    idt[n].cero      = 0;
    idt[n].tipo      = tipo;
}

void isr_manejador(struct registros *r) {
    if (manejadores[r->num]) {
        manejadores[r->num](r);
    } else if (r->num < 32) {
        kprint("Excepcion ");
        kprint_dec(r->num);
        kprint(" (");
        kprint(NOMBRES[r->num]);
        kprint(") en eip=");
        kprint_hex(r->eip);
        kprint("\n");
        if (r->num != 3) {                         /* el punto de ruptura (int 3) se puede seguir */
            kprint("PANICO: sistema detenido\n");
            for (;;) __asm__ volatile ("cli; hlt");
        }
    }
    if (r->num >= 32 && r->num < 48) irq_fin((int)r->num - 32);
}

void idt_init(void) {
    idtp.limite = sizeof(idt) - 1;
    idtp.base   = (uint32_t)&idt;
    for (int i = 0; i < 48; i++) idt_poner(i, isr_tabla[i], 0x08, 0x8E);
    __asm__ volatile ("lidt %0" : : "m"(idtp));
    kprint("IDT OK\n");
}
"""

_ISR_S = r"""; isr.s — trocitos de entrada de las interrupciones 0..47 (excepciones + IRQ)
extern isr_manejador

%macro ISR_SIN_ERROR 1
global isr%1
isr%1:
    push dword 0            ; código de error falso (para que la pila sea igual en todas)
    push dword %1
    jmp isr_comun
%endmacro

%macro ISR_CON_ERROR 1
global isr%1
isr%1:
    push dword %1           ; el procesador ya metió el código de error
    jmp isr_comun
%endmacro

ISR_SIN_ERROR 0
ISR_SIN_ERROR 1
ISR_SIN_ERROR 2
ISR_SIN_ERROR 3
ISR_SIN_ERROR 4
ISR_SIN_ERROR 5
ISR_SIN_ERROR 6
ISR_SIN_ERROR 7
ISR_CON_ERROR 8
ISR_SIN_ERROR 9
ISR_CON_ERROR 10
ISR_CON_ERROR 11
ISR_CON_ERROR 12
ISR_CON_ERROR 13
ISR_CON_ERROR 14
ISR_SIN_ERROR 15
ISR_SIN_ERROR 16
ISR_CON_ERROR 17
ISR_SIN_ERROR 18
ISR_SIN_ERROR 19
ISR_SIN_ERROR 20
ISR_CON_ERROR 21
ISR_SIN_ERROR 22
ISR_SIN_ERROR 23
ISR_SIN_ERROR 24
ISR_SIN_ERROR 25
ISR_SIN_ERROR 26
ISR_SIN_ERROR 27
ISR_SIN_ERROR 28
ISR_CON_ERROR 29
ISR_CON_ERROR 30
ISR_SIN_ERROR 31
%assign i 32
%rep 16
ISR_SIN_ERROR i
%assign i i+1
%endrep

isr_comun:
    pusha
    push ds
    push es
    push fs
    push gs
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    push esp                ; argumento: puntero a struct registros
    call isr_manejador
    add esp, 4
    pop gs
    pop fs
    pop es
    pop ds
    popa
    add esp, 8              ; quita número y código de error
    iret

section .data
global isr_tabla
isr_tabla:
%assign i 0
%rep 48
    dd isr %+ i
%assign i i+1
%endrep
"""

_PIC_C = r"""/* pic.c — remapea el PIC 8259 (IRQ 0-15 → interrupciones 32-47) y manda el fin de interrupción */
#include "io.h"
#include "idt.h"
#include "consola.h"

#define PIC1 0x20
#define PIC2 0xA0

void pic_init(void) {
    outb(PIC1, 0x11); io_wait();           /* ICW1: empezar, con ICW4 */
    outb(PIC2, 0x11); io_wait();
    outb(PIC1 + 1, 32); io_wait();         /* ICW2: el maestro empieza en 32 */
    outb(PIC2 + 1, 40); io_wait();         /*       el esclavo en 40 */
    outb(PIC1 + 1, 4); io_wait();          /* ICW3: el esclavo cuelga de la IRQ 2 */
    outb(PIC2 + 1, 2); io_wait();
    outb(PIC1 + 1, 0x01); io_wait();       /* ICW4: modo 8086 */
    outb(PIC2 + 1, 0x01); io_wait();
    outb(PIC1 + 1, 0xFC);                  /* máscara: solo IRQ 0 (temporizador) e IRQ 1 (teclado) */
    outb(PIC2 + 1, 0xFF);
    kprint("PIC OK\n");
}

void irq_fin(int irq) {
    if (irq >= 8) outb(PIC2, 0x20);
    outb(PIC1, 0x20);
}
"""

_TIMER_C = r"""/* timer.c — PIT 8254: IRQ 0 a la frecuencia pedida */
#include "io.h"
#include "idt.h"
#include "timer.h"

static volatile uint32_t tics = 0;

static void timer_tic(struct registros *r) { (void)r; tics++; }

void timer_init(uint32_t hercios) {
    uint32_t divisor = 1193182 / hercios;
    idt_poner_manejador(32, timer_tic);
    outb(0x43, 0x36);
    outb(0x40, (uint8_t)(divisor & 0xFF));
    outb(0x40, (uint8_t)((divisor >> 8) & 0xFF));
}

uint32_t timer_tics(void) { return tics; }
"""

_TIMER_H = r"""#ifndef TIMER_H
#define TIMER_H
#include <stdint.h>
void timer_init(uint32_t hercios);
uint32_t timer_tics(void);
#endif
"""

_TECLADO_C = r"""/* teclado.c — teclado PS/2 (IRQ 1): escribe en pantalla lo que tecleas */
#include "io.h"
#include "idt.h"
#include "consola.h"

static const char MAPA[128] = {
    0, 27, '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '\'', 0, '\b',
    '\t', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '`', '+', '\n',
    0, 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 0, 0, 0,
    0, '<', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '-', 0,
    '*', 0, ' '
};
static int mayus = 0;

static void teclado_irq(struct registros *r) {
    (void)r;
    uint8_t sc = inb(0x60);
    if (sc == 0x2A || sc == 0x36) { mayus = 1; return; }      /* shift pulsado */
    if (sc == 0xAA || sc == 0xB6) { mayus = 0; return; }      /* shift soltado */
    if (sc == 0x01) {                                         /* Esc: reiniciar (por el controlador del teclado) */
        kprint("\nReiniciando...\n");
        for (int i = 0; i < 100000 && (inb(0x64) & 0x02); i++) { }
        outb(0x64, 0xFE);
        return;
    }
    if (sc & 0x80) return;                                    /* tecla soltada */
    char c = (sc < 128) ? MAPA[sc] : 0;
    if (!c) return;
    if (mayus && c >= 'a' && c <= 'z') c = (char)(c - 32);
    kputc(c);
}

void teclado_init(void) {
    idt_poner_manejador(33, teclado_irq);
    kprint("Teclado OK\n");
}
"""

_MEMORIA_H = r"""#ifndef MEMORIA_H
#define MEMORIA_H
#include <stdint.h>
#include <stddef.h>
void marcos_init(uint32_t memoria_kb);
uint32_t marco_reservar(void);         /* dirección física de un marco de 4 KB libre (0 si no hay) */
void marco_liberar(uint32_t dir);
uint32_t marcos_libres(void);
void paginacion_init(void);            /* mapa identidad de los primeros 16 MB y activa la paginación */
void paginacion_mapear(uint32_t dir, uint32_t tam);   /* mapa identidad de la zona de un aparato (sin caché) */
void *kmalloc(size_t tam);
void kfree(void *p);
#endif
"""

_MEMORIA_C = r"""/* memoria.c — marcos físicos (mapa de bits), paginación (mapa identidad) y heap (lista de bloques libres) */
#include "memoria.h"
#include "consola.h"

#define MARCO 4096
#define MAX_MARCOS (4096u * 32u)                 /* hasta 512 MB */
extern uint8_t fin_kernel[];                    /* linker.ld */

static uint32_t mapa[MAX_MARCOS / 32];
static uint32_t total_marcos = 0, libres = 0;

static void poner(uint32_t m)  { mapa[m / 32] |=  (1u << (m % 32)); }
static void quitar(uint32_t m) { mapa[m / 32] &= ~(1u << (m % 32)); }
static int  ocupado(uint32_t m) { return (mapa[m / 32] >> (m % 32)) & 1u; }

void marcos_init(uint32_t memoria_kb) {
    total_marcos = (1024u + memoria_kb) / 4u;           /* 1 MB bajo + mem_upper */
    if (total_marcos > MAX_MARCOS) total_marcos = MAX_MARCOS;
    for (uint32_t i = 0; i < MAX_MARCOS / 32; i++) mapa[i] = 0xFFFFFFFFu;
    uint32_t primero = (((uint32_t)fin_kernel) + MARCO - 1) / MARCO + 16;   /* + margen para las tablas */
    libres = 0;
    for (uint32_t m = primero; m < total_marcos; m++) { quitar(m); libres++; }
}

uint32_t marco_reservar(void) {
    for (uint32_t i = 0; i < total_marcos / 32; i++) {
        if (mapa[i] == 0xFFFFFFFFu) continue;
        for (uint32_t b = 0; b < 32; b++) {
            uint32_t m = i * 32 + b;
            if (!ocupado(m)) { poner(m); libres--; return m * MARCO; }
        }
    }
    return 0;
}

void marco_liberar(uint32_t dir) {
    uint32_t m = dir / MARCO;
    if (m < total_marcos && ocupado(m)) { quitar(m); libres++; }
}

uint32_t marcos_libres(void) { return libres; }

/* ---- paginación: directorio + 4 tablas = 16 MB en mapa identidad ---- */
static uint32_t directorio[1024] __attribute__((aligned(4096)));
static uint32_t tablas[4][1024] __attribute__((aligned(4096)));

void paginacion_init(void) {
    for (int i = 0; i < 1024; i++) directorio[i] = 0x2;          /* no presente, escribible */
    for (int t = 0; t < 4; t++) {
        for (int i = 0; i < 1024; i++)
            tablas[t][i] = ((uint32_t)(t * 1024 + i) * MARCO) | 0x3;   /* presente + escribible */
        directorio[t] = ((uint32_t)tablas[t]) | 0x3;
    }
    __asm__ volatile ("mov %0, %%cr3" : : "r"(directorio));
    uint32_t cr0;
    __asm__ volatile ("mov %%cr0, %0" : "=r"(cr0));
    cr0 |= 0x80000000u;
    __asm__ volatile ("mov %0, %%cr0" : : "r"(cr0));
}

/* ---- zonas de aparatos (MMIO): tablas de reserva, sin caché (bit PCD) ---- */
static uint32_t tablas_extra[4][1024] __attribute__((aligned(4096)));
static int extra_usadas = 0;

void paginacion_mapear(uint32_t dir, uint32_t tam) {
    uint32_t fin = dir + tam;
    for (uint32_t d = dir & 0xFFC00000u; d < fin && d >= (dir & 0xFFC00000u); d += 0x400000u) {
        uint32_t i = d >> 22;
        if (!(directorio[i] & 1)) {
            if (extra_usadas >= 4) return;
            uint32_t *t = tablas_extra[extra_usadas++];
            for (uint32_t k = 0; k < 1024; k++) t[k] = (d + k * MARCO) | 0x13;   /* presente+escribible+sin caché */
            directorio[i] = ((uint32_t)t) | 0x3;
        }
        if (d >= 0xFFC00000u) break;                       /* la última zona de 4 MB: no dar la vuelta */
    }
    uint32_t cr3;
    __asm__ volatile ("mov %%cr3, %0; mov %0, %%cr3" : "=r"(cr3) : : "memory");   /* vaciar la TLB */
}

/* ---- heap: bloques con cabecera en una zona fija de 256 KB ---- */
struct bloque { uint32_t tam; uint32_t libre; struct bloque *sig; };
static uint8_t zona[256 * 1024] __attribute__((aligned(16)));
static struct bloque *lista = 0;

void *kmalloc(size_t tam) {
    tam = (tam + 15) & ~(size_t)15;
    if (!lista) {
        lista = (struct bloque *)zona;
        lista->tam = sizeof(zona) - sizeof(struct bloque);
        lista->libre = 1;
        lista->sig = 0;
    }
    for (struct bloque *b = lista; b; b = b->sig) {
        if (!b->libre || b->tam < tam) continue;
        if (b->tam >= tam + sizeof(struct bloque) + 16) {          /* se parte en dos */
            struct bloque *n = (struct bloque *)((uint8_t *)(b + 1) + tam);
            n->tam = b->tam - tam - sizeof(struct bloque);
            n->libre = 1;
            n->sig = b->sig;
            b->tam = tam;
            b->sig = n;
        }
        b->libre = 0;
        return (void *)(b + 1);
    }
    return 0;
}

void kfree(void *p) {
    if (!p) return;
    struct bloque *b = (struct bloque *)p - 1;
    b->libre = 1;
    for (struct bloque *x = lista; x; x = x->sig)                  /* junta los libres seguidos */
        while (x->libre && x->sig && x->sig->libre) {
            x->tam += sizeof(struct bloque) + x->sig->tam;
            x->sig = x->sig->sig;
        }
}
"""

_K1 = r"""/* kernel.c — etapa 1: arranca y saluda */
#include <stdint.h>
#include "consola.h"

void kernel_main(uint32_t magic, uint32_t info) {
    (void)info;
    consola_init();
    kprint("Hola desde mi SO!\n");
    if (magic == 0x2BADB002) kprint("Multiboot OK\n");
    else kprint("ERROR: numero magico de Multiboot invalido\n");
    kprint("KERNEL_LISTO\n");
    for (;;) __asm__ volatile ("hlt");
}
"""

_K2 = r"""/* kernel.c — etapa 2: con GDT propia */
#include <stdint.h>
#include "consola.h"

void gdt_init(void);

void kernel_main(uint32_t magic, uint32_t info) {
    (void)info;
    consola_init();
    kprint("Hola desde mi SO!\n");
    if (magic != 0x2BADB002) kprint("ERROR: numero magico de Multiboot invalido\n");
    gdt_init();
    kprint("KERNEL_LISTO\n");
    for (;;) __asm__ volatile ("hlt");
}
"""

_K3 = r"""/* kernel.c — etapa 3: GDT + IDT (excepciones) y una prueba con int 3 */
#include <stdint.h>
#include "consola.h"
#include "idt.h"

void gdt_init(void);

void kernel_main(uint32_t magic, uint32_t info) {
    (void)info;
    consola_init();
    kprint("Hola desde mi SO!\n");
    if (magic != 0x2BADB002) kprint("ERROR: numero magico de Multiboot invalido\n");
    gdt_init();
    idt_init();
    __asm__ volatile ("int $3");               /* prueba: el manejador la atiende y seguimos */
    kprint("Excepciones OK\n");
    kprint("KERNEL_LISTO\n");
    for (;;) __asm__ volatile ("hlt");
}
"""

_K4 = r"""/* kernel.c — etapa 4: PIC + temporizador + teclado (interrupciones de verdad) */
#include <stdint.h>
#include "consola.h"
#include "idt.h"
#include "timer.h"

void gdt_init(void);
void pic_init(void);
void teclado_init(void);

void kernel_main(uint32_t magic, uint32_t info) {
    (void)info;
    consola_init();
    kprint("Hola desde mi SO!\n");
    if (magic != 0x2BADB002) kprint("ERROR: numero magico de Multiboot invalido\n");
    gdt_init();
    idt_init();
    pic_init();
    timer_init(100);
    teclado_init();
    __asm__ volatile ("sti");
    while (timer_tics() < 10) __asm__ volatile ("hlt");
    kprint("TIMER OK (");
    kprint_dec(timer_tics());
    kprint(" tics)\n");
    kprint("KERNEL_LISTO\n");
    kprint("Escribe algo (Esc = reiniciar): ");
    for (;;) __asm__ volatile ("hlt");
}
"""

_K5 = r"""/* kernel.c — etapa 5: memoria física, paginación y heap */
#include <stdint.h>
#include "consola.h"
#include "idt.h"
#include "timer.h"
#include "memoria.h"

void gdt_init(void);
void pic_init(void);
void teclado_init(void);

struct multiboot_info { uint32_t flags, mem_lower, mem_upper; };

void kernel_main(uint32_t magic, uint32_t info) {
    consola_init();
    kprint("Hola desde mi SO!\n");
    if (magic != 0x2BADB002) kprint("ERROR: numero magico de Multiboot invalido\n");
    gdt_init();
    idt_init();
    pic_init();
    timer_init(100);
    teclado_init();

    struct multiboot_info *mb = (struct multiboot_info *)info;
    uint32_t kb = (magic == 0x2BADB002 && (mb->flags & 1)) ? mb->mem_upper : 31 * 1024;
    kprint("Memoria: ");
    kprint_dec((kb + 1024) / 1024);
    kprint(" MB\n");
    marcos_init(kb);
    uint32_t a = marco_reservar(), b = marco_reservar();
    marco_liberar(a);
    uint32_t c = marco_reservar();
    if (a && b && a != b && c == a) kprint("MARCOS OK\n");
    else kprint("ERROR en los marcos\n");

    paginacion_init();
    volatile uint32_t *prueba = (volatile uint32_t *)0x00A00000;   /* 10 MB: mapeado en identidad */
    *prueba = 0xCAFEBABE;
    if (*prueba == 0xCAFEBABE) kprint("PAGINACION OK\n");

    char *p = kmalloc(100), *q = kmalloc(200);
    kfree(p);
    char *r = kmalloc(50);
    if (p && q && p != q && r == p) kprint("HEAP OK\n");
    else kprint("ERROR en el heap\n");

    __asm__ volatile ("sti");
    while (timer_tics() < 5) __asm__ volatile ("hlt");
    kprint("KERNEL_LISTO\n");
    kprint("Escribe algo (Esc = reiniciar): ");
    for (;;) __asm__ volatile ("hlt");
}
"""

_PCI_H = r"""/* pci.h — el bus PCI: qué aparatos tiene el ordenador */
#ifndef PCI_H
#define PCI_H
#include <stdint.h>

struct pci_disp {
    uint8_t  bus, disp, func;
    uint16_t vendedor, aparato;
    uint8_t  clase, subclase, irq;
    uint32_t bar0;
};

uint32_t pci_leer(uint8_t bus, uint8_t disp, uint8_t func, uint8_t off);
void pci_escribir(uint8_t bus, uint8_t disp, uint8_t func, uint8_t off, uint32_t valor);
int pci_buscar(uint16_t vendedor, uint16_t aparato, struct pci_disp *d);   /* 1 si lo encuentra */
int pci_buscar_clase(uint8_t clase, uint8_t subclase, struct pci_disp *d); /* el primero de esa clase */
int pci_listar(void);                                                    /* los escribe y dice cuántos */

#endif
"""

_PCI_C = r"""/* pci.c — recorre el bus PCI con el mecanismo de configuración 1 (puertos 0xCF8 / 0xCFC) */
#include "pci.h"
#include "io.h"
#include "consola.h"

uint32_t pci_leer(uint8_t bus, uint8_t disp, uint8_t func, uint8_t off) {
    uint32_t dir = (1u << 31) | ((uint32_t)bus << 16) | ((uint32_t)disp << 11) | ((uint32_t)func << 8) | (off & 0xFC);
    outl(0xCF8, dir);
    return inl(0xCFC);
}

void pci_escribir(uint8_t bus, uint8_t disp, uint8_t func, uint8_t off, uint32_t valor) {
    uint32_t dir = (1u << 31) | ((uint32_t)bus << 16) | ((uint32_t)disp << 11) | ((uint32_t)func << 8) | (off & 0xFC);
    outl(0xCF8, dir);
    outl(0xCFC, valor);
}

static void leer_disp(uint8_t b, uint8_t d, uint8_t f, uint32_t id, struct pci_disp *x) {
    uint32_t clase = pci_leer(b, d, f, 0x08);
    x->bus = b; x->disp = d; x->func = f;
    x->vendedor = id & 0xFFFF; x->aparato = id >> 16;
    x->clase = clase >> 24; x->subclase = (clase >> 16) & 0xFF;
    x->bar0 = pci_leer(b, d, f, 0x10);
    x->irq = pci_leer(b, d, f, 0x3C) & 0xFF;
}

static const char *nombre_clase(uint8_t c, uint8_t s) {
    switch (c) {
    case 0x01: return s == 0x01 ? "controlador de disco IDE" : (s == 0x06 ? "controlador de disco SATA (AHCI)" : "almacenamiento");
    case 0x02: return "tarjeta de red";
    case 0x03: return "tarjeta grafica";
    case 0x04: return "sonido / multimedia";
    case 0x06: return s == 0x00 ? "puente principal" : (s == 0x01 ? "puente ISA" : "puente");
    case 0x0C: return s == 0x03 ? "controlador USB" : "bus serie";
    case 0x0D: return "inalambrico (WiFi)";
    default:   return "otro aparato";
    }
}

static void hex4(uint16_t v) {
    const char *h = "0123456789abcdef";
    for (int s = 12; s >= 0; s -= 4) kputc(h[(v >> s) & 0xF]);
}

static int recorrer(uint16_t ven, uint16_t apa, struct pci_disp *encontrado, int escribir, int por_clase) {
    int n = 0;
    for (int b = 0; b < 256; b++) {
        for (int d = 0; d < 32; d++) {
            uint32_t id0 = pci_leer(b, d, 0, 0);
            if ((id0 & 0xFFFF) == 0xFFFF) continue;
            int funcs = (pci_leer(b, d, 0, 0x0C) >> 16) & 0x80 ? 8 : 1;   /* aparato con varias funciones */
            for (int f = 0; f < funcs; f++) {
                uint32_t id = pci_leer(b, d, f, 0);
                if ((id & 0xFFFF) == 0xFFFF) continue;
                struct pci_disp x;
                leer_disp(b, d, f, id, &x);
                n++;
                if (escribir) {
                    kprint("  PCI ");
                    kprint_dec(b); kputc(':'); kprint_dec(d); kputc('.'); kprint_dec(f);
                    kputc(' '); hex4(x.vendedor); kputc(':'); hex4(x.aparato);
                    kprint("  "); kprint(nombre_clase(x.clase, x.subclase)); kputc('\n');
                }
                if (encontrado && (por_clase ? (x.clase == (ven >> 8) && x.subclase == (ven & 0xFF))
                                             : (x.vendedor == ven && x.aparato == apa))) { *encontrado = x; return 1; }
            }
        }
    }
    return encontrado ? 0 : n;
}

int pci_buscar(uint16_t vendedor, uint16_t aparato, struct pci_disp *d) {
    return recorrer(vendedor, aparato, d, 0, 0);
}

int pci_buscar_clase(uint8_t clase, uint8_t subclase, struct pci_disp *d) {
    return recorrer((uint16_t)((clase << 8) | subclase), 0, d, 0, 1);
}

int pci_listar(void) {
    int n = recorrer(0, 0, 0, 1, 0);
    kprint("PCI OK (");
    kprint_dec((uint32_t)n);
    kprint(" aparatos)\n");
    return n;
}
"""

_DISCO_H = r"""/* disco.h — disco ATA por el método PIO (el más sencillo) */
#ifndef DISCO_H
#define DISCO_H
#include <stdint.h>
int disco_init(void);                                  /* 1 si hay disco ATA en el canal primario */
int disco_leer(uint32_t lba, uint8_t *buf);            /* 512 bytes; 0 = bien */
int disco_escribir(uint32_t lba, const uint8_t *buf);  /* 512 bytes; 0 = bien */
void disco_probar(void);
#endif
"""

_DISCO_C = r"""/* disco.c — disco ATA en el canal primario (puertos 0x1F0-0x1F7) por PIO, LBA28.
   SEGURIDAD: solo ESCRIBE si el sector 0 tiene la firma «KIRADISK» (el disco de pruebas de QEMU). En el disco de
   tu ordenador de verdad solo LEE: nunca escribe nada en él. */
#include "disco.h"
#include "io.h"
#include "consola.h"

#define ATA 0x1F0
static uint8_t sector[512];

static void espera400(void) { for (int i = 0; i < 4; i++) inb(ATA + 7); }

static int esperar_listo(void) {               /* 0 = listo para datos; <0 = error / sin disco */
    for (int i = 0; i < 1000000; i++) {
        uint8_t s = inb(ATA + 7);
        if (s == 0xFF) return -1;                 /* no hay nada conectado */
        if (s & 0x80) continue;                   /* ocupado */
        if (s & 0x21) return -2;                  /* error */
        if (s & 0x08) return 0;                   /* datos listos */
    }
    return -3;
}

static int esperar_libre(void) {
    for (int i = 0; i < 1000000; i++) {
        uint8_t s = inb(ATA + 7);
        if (s == 0xFF) return -1;
        if (!(s & 0x80)) return (s & 0x21) ? -2 : 0;
    }
    return -3;
}

static uint32_t total_sectores = 0;
static char modelo[41];

int disco_init(void) {
    outb(ATA + 6, 0xA0);                      /* disco maestro */
    espera400();
    if (inb(ATA + 7) == 0xFF) return 0;       /* el canal está vacío (o el disco va por AHCI) */
    outb(ATA + 2, 0); outb(ATA + 3, 0); outb(ATA + 4, 0); outb(ATA + 5, 0);
    outb(ATA + 7, 0xEC);                      /* IDENTIFY */
    if (inb(ATA + 7) == 0) return 0;
    if (esperar_libre() < 0) return 0;
    if (inb(ATA + 4) || inb(ATA + 5)) return 0;   /* no es ATA (CD o SATA en otro modo) */
    if (esperar_listo() < 0) return 0;
    uint16_t id[256];
    for (int i = 0; i < 256; i++) id[i] = inw(ATA);
    total_sectores = (uint32_t)id[60] | ((uint32_t)id[61] << 16);
    for (int i = 0; i < 20; i++) { modelo[2 * i] = (char)(id[27 + i] >> 8); modelo[2 * i + 1] = (char)(id[27 + i] & 0xFF); }
    modelo[40] = 0;
    for (int i = 39; i >= 0 && modelo[i] == ' '; i--) modelo[i] = 0;
    return 1;
}

static void preparar(uint32_t lba, uint8_t orden) {
    outb(ATA + 6, (uint8_t)(0xE0 | ((lba >> 24) & 0x0F)));
    espera400();
    outb(ATA + 2, 1);
    outb(ATA + 3, (uint8_t)lba);
    outb(ATA + 4, (uint8_t)(lba >> 8));
    outb(ATA + 5, (uint8_t)(lba >> 16));
    outb(ATA + 7, orden);
}

int disco_leer(uint32_t lba, uint8_t *buf) {
    preparar(lba, 0x20);
    if (esperar_listo() < 0) return -1;
    for (int i = 0; i < 256; i++) { uint16_t w = inw(ATA); buf[2 * i] = (uint8_t)w; buf[2 * i + 1] = (uint8_t)(w >> 8); }
    return 0;
}

int disco_escribir(uint32_t lba, const uint8_t *buf) {
    preparar(lba, 0x30);
    if (esperar_listo() < 0) return -1;
    for (int i = 0; i < 256; i++) outw(ATA, (uint16_t)(buf[2 * i] | (buf[2 * i + 1] << 8)));
    outb(ATA + 7, 0xE7);                      /* vaciar la caché del disco */
    return esperar_libre();
}

static int igual(const uint8_t *a, const char *b, int n) {
    for (int i = 0; i < n; i++) if (a[i] != (uint8_t)b[i]) return 0;
    return 1;
}

void disco_probar(void) {
    if (!disco_init()) {
        kprint("Disco: no hay disco ATA en el canal primario (en un portatil con SATA en AHCI haria falta otro driver)\n");
        return;
    }
    kprint("Disco: ");
    kprint(modelo);
    kprint(", ");
    kprint_dec(total_sectores / 2048);
    kprint(" MB\n");
    if (disco_leer(0, sector) != 0) { kprint("DISCO FALLA al leer el sector 0\n"); return; }
    if (!igual(sector, "KIRADISK", 8)) {
        kprint("Disco ajeno (no es el de pruebas): solo leo, NO escribo nada en el\n");
        kprint("DISCO OK (solo lectura)\n");
        return;
    }
    kprint("Sector 0: ");
    for (int i = 0; i < 60 && sector[i] >= 32 && sector[i] < 127; i++) kputc((char)sector[i]);
    kputc('\n');
    static uint8_t prueba[512], vuelta[512];
    for (int i = 0; i < 512; i++) prueba[i] = (uint8_t)(i * 7 + 3);
    if (disco_escribir(1, prueba) != 0 || disco_leer(1, vuelta) != 0) { kprint("DISCO FALLA al escribir\n"); return; }
    for (int i = 0; i < 512; i++) if (prueba[i] != vuelta[i]) { kprint("DISCO FALLA: lo leido no es lo escrito\n"); return; }
    kprint("DISCO OK: leo y escribo sectores\n");
}
"""

_RED_H = r"""/* red.h — tarjeta de red Intel e1000 (la que pone QEMU) */
#ifndef RED_H
#define RED_H
void red_probar(void);
#endif
"""

_RED_C = r"""/* red.c — driver de la tarjeta Intel e1000 (82540EM): lee su MAC, monta las colas de envío y recepción y pregunta
   por ARP quién es el router virtual de QEMU (10.0.2.2). QEMU corre con la red AISLADA (restrict=on): no sale a
   internet ni ve tu casa. */
#include <stdint.h>
#include "red.h"
#include "pci.h"
#include "consola.h"
#include "memoria.h"
#include "timer.h"

#define CTRL   0x0000
#define EERD   0x0014
#define ICR    0x00C0
#define IMC    0x00D8
#define RCTL   0x0100
#define TCTL   0x0400
#define TIPG   0x0410
#define RDBAL  0x2800
#define RDBAH  0x2804
#define RDLEN  0x2808
#define RDH    0x2810
#define RDT    0x2818
#define TDBAL  0x3800
#define TDBAH  0x3804
#define TDLEN  0x3808
#define TDH    0x3810
#define TDT    0x3818
#define MTA    0x5200
#define RAL    0x5400
#define RAH    0x5404

#define NRX 32
#define NTX 8

struct rx_desc { uint64_t dir; uint16_t largo; uint16_t suma; uint8_t estado; uint8_t errores; uint16_t especial; } __attribute__((packed));
struct tx_desc { uint64_t dir; uint16_t largo; uint8_t cso; uint8_t orden; uint8_t estado; uint8_t css; uint16_t especial; } __attribute__((packed));

static volatile struct rx_desc rx[NRX] __attribute__((aligned(16)));
static volatile struct tx_desc tx[NTX] __attribute__((aligned(16)));
static uint8_t rx_buf[NRX][2048] __attribute__((aligned(16)));
static uint8_t tx_buf[NTX][2048] __attribute__((aligned(16)));
static uint32_t base = 0;
static uint8_t mac[6];
static int rx_cur = 0, tx_cur = 0;

static void escribe(uint32_t reg, uint32_t v) { *(volatile uint32_t *)(base + reg) = v; }
static uint32_t lee(uint32_t reg) { return *(volatile uint32_t *)(base + reg); }

static void hex2(uint8_t v) { const char *h = "0123456789abcdef"; kputc(h[v >> 4]); kputc(h[v & 0xF]); }
static void escribe_mac(const uint8_t *m) { for (int i = 0; i < 6; i++) { if (i) kputc(':'); hex2(m[i]); } }

static int eeprom(uint8_t dir, uint16_t *dato) {
    escribe(EERD, 1u | ((uint32_t)dir << 8));
    for (int i = 0; i < 100000; i++) {
        uint32_t v = lee(EERD);
        if (v & (1u << 4)) { *dato = (uint16_t)(v >> 16); return 1; }
    }
    return 0;
}

static void leer_mac(void) {
    uint16_t w;
    if (eeprom(0, &w)) {
        mac[0] = w & 0xFF; mac[1] = w >> 8;
        eeprom(1, &w); mac[2] = w & 0xFF; mac[3] = w >> 8;
        eeprom(2, &w); mac[4] = w & 0xFF; mac[5] = w >> 8;
    } else {
        uint32_t l = lee(RAL), h = lee(RAH);
        for (int i = 0; i < 4; i++) mac[i] = (uint8_t)(l >> (8 * i));
        mac[4] = (uint8_t)h; mac[5] = (uint8_t)(h >> 8);
    }
}

static void montar_colas(void) {
    for (int i = 0; i < NRX; i++) { rx[i].dir = (uint32_t)rx_buf[i]; rx[i].estado = 0; }
    escribe(RDBAL, (uint32_t)rx); escribe(RDBAH, 0);
    escribe(RDLEN, NRX * sizeof(struct rx_desc));
    escribe(RDH, 0); escribe(RDT, NRX - 1);
    /* EN | UPE | MPE | BAM | SECRC, búfer de 2048 */
    escribe(RCTL, (1u << 1) | (1u << 3) | (1u << 4) | (1u << 15) | (1u << 26));
    for (int i = 0; i < NTX; i++) { tx[i].dir = (uint32_t)tx_buf[i]; tx[i].orden = 0; tx[i].estado = 1; }
    escribe(TDBAL, (uint32_t)tx); escribe(TDBAH, 0);
    escribe(TDLEN, NTX * sizeof(struct tx_desc));
    escribe(TDH, 0); escribe(TDT, 0);
    escribe(TCTL, (1u << 1) | (1u << 3) | (0x10u << 4) | (0x40u << 12));   /* EN | PSP | CT | COLD */
    escribe(TIPG, 0x0060200A);
}

static void enviar(const uint8_t *datos, uint16_t largo) {
    uint8_t *b = tx_buf[tx_cur];
    for (int i = 0; i < largo; i++) b[i] = datos[i];
    for (int i = largo; i < 60; i++) b[i] = 0;               /* una trama Ethernet mide al menos 60 bytes */
    if (largo < 60) largo = 60;
    tx[tx_cur].largo = largo;
    tx[tx_cur].orden = 0x01 | 0x02 | 0x08;                   /* EOP | IFCS | RS */
    tx[tx_cur].estado = 0;
    tx_cur = (tx_cur + 1) % NTX;
    escribe(TDT, tx_cur);
}

void red_probar(void) {
    struct pci_disp d;
    if (!pci_buscar(0x8086, 0x100E, &d)) {
        kprint("Red: no hay tarjeta Intel e1000 (en tu portatil seguramente es otra marca: haria falta su driver)\n");
        return;
    }
    uint32_t orden = pci_leer(d.bus, d.disp, d.func, 0x04);
    pci_escribir(d.bus, d.disp, d.func, 0x04, orden | 0x06);   /* memoria + bus master (la tarjeta escribe en la RAM) */
    base = d.bar0 & 0xFFFFFFF0u;
    paginacion_mapear(base, 0x20000);
    escribe(CTRL, lee(CTRL) | (1u << 26));                      /* reinicio de la tarjeta */
    for (volatile int i = 0; i < 200000; i++) { }
    escribe(IMC, 0xFFFFFFFFu);                                  /* sin interrupciones: miramos nosotros */
    (void)lee(ICR);
    escribe(CTRL, lee(CTRL) | (1u << 6) | (1u << 5));           /* enlace arriba (SLU | ASDE) */
    for (int i = 0; i < 128; i++) escribe(MTA + 4 * i, 0);
    leer_mac();
    escribe(RAL, mac[0] | (mac[1] << 8) | (mac[2] << 16) | ((uint32_t)mac[3] << 24));
    escribe(RAH, mac[4] | (mac[5] << 8) | (1u << 31));
    kprint("Red: tarjeta e1000, MAC ");
    escribe_mac(mac);
    kputc('\n');
    montar_colas();

    /* ARP: «¿quién tiene 10.0.2.2? díselo a 10.0.2.15» */
    uint8_t p[42];
    for (int i = 0; i < 6; i++) { p[i] = 0xFF; p[6 + i] = mac[i]; }
    p[12] = 0x08; p[13] = 0x06;                                 /* tipo ARP */
    p[14] = 0; p[15] = 1; p[16] = 0x08; p[17] = 0; p[18] = 6; p[19] = 4; p[20] = 0; p[21] = 1;   /* petición */
    for (int i = 0; i < 6; i++) { p[22 + i] = mac[i]; p[32 + i] = 0; }
    p[28] = 10; p[29] = 0; p[30] = 2; p[31] = 15;               /* yo: 10.0.2.15 */
    p[38] = 10; p[39] = 0; p[40] = 2; p[41] = 2;                /* busco: 10.0.2.2 */
    enviar(p, sizeof(p));

    uint32_t fin = timer_tics() + 300;                          /* 3 segundos como mucho */
    while (timer_tics() < fin) {
        if (rx[rx_cur].estado & 1) {
            uint8_t *r = rx_buf[rx_cur];
            int es_arp = r[12] == 0x08 && r[13] == 0x06 && r[21] == 2 &&
                         r[28] == 10 && r[29] == 0 && r[30] == 2 && r[31] == 2;
            rx[rx_cur].estado = 0;
            escribe(RDT, rx_cur);
            rx_cur = (rx_cur + 1) % NRX;
            if (es_arp) {
                kprint("RED OK: el router virtual 10.0.2.2 me ha contestado (MAC ");
                escribe_mac(r + 22);
                kprint(")\n");
                return;
            }
        } else {
            __asm__ volatile ("hlt");
        }
    }
    kprint("RED FALLA: nadie contesto al ARP\n");
}
"""

_AHCI_H = r"""/* ahci.h — disco SATA por AHCI (el modo de los portátiles modernos): SOLO LECTURA */
#ifndef AHCI_H
#define AHCI_H
void ahci_probar(void);
#endif
"""

_AHCI_C = r"""/* ahci.c — driver AHCI de SOLO LECTURA: encuentra el controlador SATA, mira qué hay en cada puerto, identifica
   el disco (modelo y tamaño) y lee su tabla de particiones (MBR o GPT).
   SEGURIDAD: este código NO tiene ninguna orden de escritura. Solo usa IDENTIFY (0xEC) y READ DMA EXT (0x25), y la
   tabla de descriptores siempre pide «del disco a la memoria». Tu Xubuntu y tus archivos no se tocan. */
#include <stdint.h>
#include "ahci.h"
#include "pci.h"
#include "consola.h"
#include "memoria.h"
#include "timer.h"

/* registros generales */
#define CAP   0x00
#define GHC   0x04
#define IS    0x08
#define PI    0x0C
#define VS    0x10
#define CAP2  0x24
#define BOHC  0x28
/* registros de cada puerto (0x100 + n*0x80) */
#define P_CLB  0x00
#define P_CLBU 0x04
#define P_FB   0x08
#define P_FBU  0x0C
#define P_IS   0x10
#define P_IE   0x14
#define P_CMD  0x18
#define P_TFD  0x20
#define P_SIG  0x24
#define P_SSTS 0x28
#define P_SERR 0x30
#define P_CI   0x38

#define SIG_ATA   0x00000101u
#define SIG_ATAPI 0xEB140101u

struct cabecera { uint32_t dw0, prdbc, ctba, ctbau, res[4]; } __attribute__((packed));
struct prd { uint32_t dba, dbau, res, dbc; } __attribute__((packed));
struct tabla { uint8_t cfis[64]; uint8_t acmd[16]; uint8_t res[48]; struct prd prdt[1]; } __attribute__((packed));

static volatile struct cabecera lista[32] __attribute__((aligned(1024)));
static volatile uint8_t recibidos[256] __attribute__((aligned(256)));
static volatile struct tabla tab __attribute__((aligned(128)));
static uint8_t buf[512] __attribute__((aligned(16)));
static uint8_t entradas[512] __attribute__((aligned(16)));
static uint32_t abar = 0;

static uint32_t lee(uint32_t r) { return *(volatile uint32_t *)(abar + r); }
static void escribe(uint32_t r, uint32_t v) { *(volatile uint32_t *)(abar + r) = v; }
static uint32_t plee(int p, uint32_t r) { return lee(0x100 + 0x80 * (uint32_t)p + r); }
static void pescribe(int p, uint32_t r, uint32_t v) { escribe(0x100 + 0x80 * (uint32_t)p + r, v); }

static void ceros(volatile void *d, uint32_t n) { volatile uint8_t *b = d; for (uint32_t i = 0; i < n; i++) b[i] = 0; }

static int esperar(int p, uint32_t reg, uint32_t bits, int puestos, uint32_t tics) {
    uint32_t fin = timer_tics() + tics;
    for (;;) {
        uint32_t v = plee(p, reg) & bits;
        if (puestos ? v == bits : v == 0) return 0;
        if (timer_tics() > fin) return -1;
    }
}

static void parar(int p) {
    pescribe(p, P_CMD, plee(p, P_CMD) & ~1u);            /* ST = 0 */
    esperar(p, P_CMD, 1u << 15, 0, 60);                  /* CR libre */
    pescribe(p, P_CMD, plee(p, P_CMD) & ~(1u << 4));     /* FRE = 0 */
    esperar(p, P_CMD, 1u << 14, 0, 60);                  /* FR libre */
}

static int arrancar(int p) {
    parar(p);
    ceros(lista, sizeof(lista)); ceros(recibidos, sizeof(recibidos));
    pescribe(p, P_CLB, (uint32_t)lista); pescribe(p, P_CLBU, 0);
    pescribe(p, P_FB, (uint32_t)recibidos); pescribe(p, P_FBU, 0);
    pescribe(p, P_SERR, 0xFFFFFFFFu);
    pescribe(p, P_IS, 0xFFFFFFFFu);
    pescribe(p, P_IE, 0);                                /* sin interrupciones: miramos nosotros */
    pescribe(p, P_CMD, plee(p, P_CMD) | (1u << 4));      /* FRE */
    pescribe(p, P_CMD, plee(p, P_CMD) | 1u);             /* ST */
    return 0;
}

/* Manda una orden de LECTURA (del disco a la memoria) y espera. 0 = bien. */
static int orden_lectura(int p, uint8_t cmd, uint32_t lba, uint8_t *destino) {
    if (esperar(p, P_TFD, 0x88, 0, 100) != 0) return -1;     /* BSY y DRQ libres */
    ceros(&tab, sizeof(tab));
    lista[0].dw0 = 5u | (1u << 16);                           /* 5 dwords de FIS, W=0 (leer), 1 descriptor */
    lista[0].prdbc = 0;
    lista[0].ctba = (uint32_t)&tab; lista[0].ctbau = 0;
    tab.prdt[0].dba = (uint32_t)destino; tab.prdt[0].dbau = 0;
    tab.prdt[0].dbc = 511;                                    /* 512 bytes */
    tab.cfis[0] = 0x27; tab.cfis[1] = 0x80; tab.cfis[2] = cmd;
    tab.cfis[4] = (uint8_t)lba; tab.cfis[5] = (uint8_t)(lba >> 8); tab.cfis[6] = (uint8_t)(lba >> 16);
    tab.cfis[7] = 0x40;                                       /* modo LBA */
    tab.cfis[8] = (uint8_t)(lba >> 24);
    tab.cfis[12] = 1;                                         /* 1 sector */
    pescribe(p, P_IS, 0xFFFFFFFFu);
    pescribe(p, P_CI, 1);
    uint32_t fin = timer_tics() + 300;
    while (plee(p, P_CI) & 1) {
        if (plee(p, P_IS) & (1u << 30)) return -2;           /* error del disco */
        if (timer_tics() > fin) return -3;
    }
    if ((plee(p, P_IS) & (1u << 30)) || (plee(p, P_TFD) & 1)) return -2;
    return 0;
}

static void texto_id(const uint16_t *id, int desde, int palabras, char *sal) {
    int n = 0;
    for (int i = 0; i < palabras; i++) { sal[n++] = (char)(id[desde + i] >> 8); sal[n++] = (char)(id[desde + i] & 0xFF); }
    sal[n] = 0;
    while (n > 0 && sal[n - 1] == ' ') sal[--n] = 0;
}

static void tamano(uint32_t mb) {
    if (mb >= 10240) { kprint_dec(mb / 1024); kprint(" GB"); }
    else { kprint_dec(mb); kprint(" MB"); }
}

static uint32_t u32(const uint8_t *b) { return b[0] | (b[1] << 8) | (b[2] << 16) | ((uint32_t)b[3] << 24); }

static const char *tipo_mbr(uint8_t t) {
    switch (t) {
    case 0x83: return "Linux";
    case 0x82: return "Linux swap";
    case 0x8E: return "Linux LVM";
    case 0x07: return "NTFS (Windows)";
    case 0x0B: case 0x0C: return "FAT32";
    case 0x05: case 0x0F: return "extendida";
    case 0x27: return "recuperacion de Windows";
    case 0xEF: return "EFI";
    default:   return "otra";
    }
}

static const char *tipo_gpt(uint32_t g) {
    switch (g) {
    case 0x0FC63DAFu: return "Linux";
    case 0x0657FD6Du: return "Linux swap";
    case 0xE6D6D379u: return "Linux LVM";
    case 0xC12A7328u: return "EFI";
    case 0x21686148u: return "arranque BIOS";
    case 0xEBD0A0A2u: return "datos de Windows";
    case 0xE3C9E316u: return "reservada de Windows";
    case 0xDE94BBA4u: return "recuperacion de Windows";
    default:          return "otra";
    }
}

static void particion(int n, const char *tipo, uint32_t sectores) {
    kprint("      "); kprint_dec((uint32_t)n); kprint(": "); kprint(tipo); kprint(", "); tamano((sectores + 1024) / 2048); kputc('\n');
}

static int leer_gpt(int p) {
    if (orden_lectura(p, 0x25, 1, buf) != 0) return 0;
    if (!(buf[0] == 'E' && buf[1] == 'F' && buf[2] == 'I' && buf[3] == ' ' && buf[4] == 'P')) return 0;
    uint32_t lba = u32(buf + 72), num = u32(buf + 80), tam = u32(buf + 84);
    if (tam < 128 || tam > 512 || num == 0) return 0;
    kprint("    Tabla GPT\n");
    int n = 0;
    uint32_t por_sector = 512 / tam, mirar = num < 32 ? num : 32;     /* las 32 primeras bastan */
    for (uint32_t i = 0; i < mirar; i++) {
        if (i % por_sector == 0 && orden_lectura(p, 0x25, lba + i / por_sector, entradas) != 0) break;
        const uint8_t *e = entradas + (i % por_sector) * tam;
        uint32_t tipo = u32(e);
        if (!tipo && !u32(e + 4)) continue;
        uint32_t ini = u32(e + 32), fin = u32(e + 40);
        if (++n <= 8) particion(n, tipo_gpt(tipo), fin >= ini ? fin - ini + 1 : 0);
    }
    if (n > 8) { kprint("      … y "); kprint_dec((uint32_t)(n - 8)); kprint(" mas\n"); }
    if (!n) kprint("      (sin particiones)\n");
    return 1;
}

static void leer_tabla(int p) {
    if (orden_lectura(p, 0x25, 0, buf) != 0) { kprint("    no puedo leer el sector 0\n"); return; }
    if (buf[510] != 0x55 || buf[511] != 0xAA) { kprint("    sin tabla de particiones\n"); return; }
    if (buf[446 + 4] == 0xEE && leer_gpt(p)) return;           /* MBR protector: es GPT */
    if (orden_lectura(p, 0x25, 0, buf) != 0) return;
    kprint("    Tabla MBR\n");
    int n = 0;
    for (int i = 0; i < 4; i++) {
        const uint8_t *e = buf + 446 + 16 * i;
        if (!e[4]) continue;
        particion(i + 1, tipo_mbr(e[4]), u32(e + 12));
        n++;
    }
    if (!n) kprint("      (sin particiones)\n");
}

static int mirar_puerto(int p) {
    uint32_t ssts = plee(p, P_SSTS);
    if ((ssts & 0xF) != 3) return 0;                             /* no hay nada enchufado */
    kprint("  Puerto "); kprint_dec((uint32_t)p); kprint(": ");
    if (((ssts >> 8) & 0xF) != 1) { kprint("aparato dormido (no lo despierto)\n"); return 0; }
    uint32_t sig = plee(p, P_SIG);
    if (sig == SIG_ATAPI) { kprint("lector de CD/DVD (no lo leo)\n"); return 0; }
    if (sig != SIG_ATA) { kprint("otro aparato SATA\n"); return 0; }
    arrancar(p);
    uint16_t id[256];
    if (orden_lectura(p, 0xEC, 0, (uint8_t *)id) != 0) { kprint("disco que no contesta\n"); parar(p); return 0; }
    char modelo[41];
    texto_id(id, 27, 20, modelo);
    uint32_t lo, hi;
    if (id[83] & (1u << 10)) { lo = id[100] | ((uint32_t)id[101] << 16); hi = id[102] | ((uint32_t)id[103] << 16); }
    else { lo = id[60] | ((uint32_t)id[61] << 16); hi = 0; }
    kprint("disco "); kprint(modelo); kprint(", "); tamano((hi << 21) | (lo >> 11)); kputc('\n');
    leer_tabla(p);
    parar(p);
    return 1;
}

void ahci_probar(void) {
    struct pci_disp d;
    if (!pci_buscar_clase(0x01, 0x06, &d)) {
        kprint("AHCI: no hay controlador SATA en modo AHCI\n");
        return;
    }
    uint32_t orden = pci_leer(d.bus, d.disp, d.func, 0x04);
    pci_escribir(d.bus, d.disp, d.func, 0x04, orden | 0x06);      /* memoria + bus master */
    abar = pci_leer(d.bus, d.disp, d.func, 0x24) & 0xFFFFF000u;   /* BAR5 */
    if (!abar) { kprint("AHCI: el controlador no tiene direccion\n"); return; }
    paginacion_mapear(abar, 0x1100);
    if ((lee(CAP2) & 1) && (lee(BOHC) & 1)) {                     /* la BIOS aún lo maneja: se lo pido */
        escribe(BOHC, lee(BOHC) | 2);
        uint32_t fin = timer_tics() + 200;
        while ((lee(BOHC) & 1) && timer_tics() < fin) { }
    }
    escribe(GHC, (lee(GHC) | (1u << 31)) & ~2u);                  /* modo AHCI, sin interrupciones */
    uint32_t vs = lee(VS), pi = lee(PI);
    kprint("AHCI: controlador ");
    kprint_dec(vs >> 16); kputc('.'); kprint_dec((vs >> 8) & 0xFF);
    kprint(", "); kprint_dec((lee(CAP) & 0x1F) + 1); kprint(" puertos\n");
    int discos = 0;
    for (int p = 0; p < 32; p++) if (pi & (1u << p)) discos += mirar_puerto(p);
    if (!discos) { kprint("AHCI: no he encontrado discos\n"); return; }
    kprint("AHCI OK (solo lectura: "); kprint_dec((uint32_t)discos); kprint(discos == 1 ? " disco)\n" : " discos)\n");
}
"""
_AHCI2_H = r"""/* ahci.h (v2) — disco SATA por AHCI: SOLO LECTURA */
#ifndef AHCI_H
#define AHCI_H
#include <stdint.h>
void ahci_probar(void);                                                      /* busca discos y particiones */
int ahci_leer(int disco, uint32_t lba, uint32_t n, void *destino);           /* n sectores (1..16); 0 = bien */
int ahci_particion(int i, int *disco, uint32_t *inicio, uint32_t *sectores, int *es_linux);   /* 0 = no hay más */
int ahci_num_discos(void);
void ahci_resumen(void);
#endif
"""

_AHCI2_C = r"""/* ahci.c (v2, etapa 10+) — driver AHCI de SOLO LECTURA: además recuerda los discos y sus particiones y deja leer
   varios sectores seguidos (para el sistema de archivos). Encuentra el controlador SATA, mira qué hay en cada puerto, identifica
   el disco (modelo y tamaño) y lee su tabla de particiones (MBR o GPT).
   SEGURIDAD: este código NO tiene ninguna orden de escritura. Solo usa IDENTIFY (0xEC) y READ DMA EXT (0x25), y la
   tabla de descriptores siempre pide «del disco a la memoria». Tu Xubuntu y tus archivos no se tocan. */
#include <stdint.h>
#include "ahci.h"
#include "pci.h"
#include "consola.h"
#include "memoria.h"
#include "timer.h"

/* registros generales */
#define CAP   0x00
#define GHC   0x04
#define IS    0x08
#define PI    0x0C
#define VS    0x10
#define CAP2  0x24
#define BOHC  0x28
/* registros de cada puerto (0x100 + n*0x80) */
#define P_CLB  0x00
#define P_CLBU 0x04
#define P_FB   0x08
#define P_FBU  0x0C
#define P_IS   0x10
#define P_IE   0x14
#define P_CMD  0x18
#define P_TFD  0x20
#define P_SIG  0x24
#define P_SSTS 0x28
#define P_SERR 0x30
#define P_CI   0x38

#define SIG_ATA   0x00000101u
#define SIG_ATAPI 0xEB140101u

struct cabecera { uint32_t dw0, prdbc, ctba, ctbau, res[4]; } __attribute__((packed));
struct prd { uint32_t dba, dbau, res, dbc; } __attribute__((packed));
struct tabla { uint8_t cfis[64]; uint8_t acmd[16]; uint8_t res[48]; struct prd prdt[1]; } __attribute__((packed));

static volatile struct cabecera lista[32] __attribute__((aligned(1024)));
static volatile uint8_t recibidos[256] __attribute__((aligned(256)));
static volatile struct tabla tab __attribute__((aligned(128)));
static uint8_t buf[512] __attribute__((aligned(16)));
static uint8_t entradas[512] __attribute__((aligned(16)));
static uint32_t abar = 0;
static int puerto_activo = -1;

struct disco_ahci { int puerto; uint32_t mb; char modelo[41]; };
struct part_ahci { int disco; uint32_t inicio, sectores; int es_linux; };
static struct disco_ahci discos[4];
static struct part_ahci parts[16];
static int ndiscos = 0, nparts = 0, disco_actual = 0;

static uint32_t lee(uint32_t r) { return *(volatile uint32_t *)(abar + r); }
static void escribe(uint32_t r, uint32_t v) { *(volatile uint32_t *)(abar + r) = v; }
static uint32_t plee(int p, uint32_t r) { return lee(0x100 + 0x80 * (uint32_t)p + r); }
static void pescribe(int p, uint32_t r, uint32_t v) { escribe(0x100 + 0x80 * (uint32_t)p + r, v); }

static void ceros(volatile void *d, uint32_t n) { volatile uint8_t *b = d; for (uint32_t i = 0; i < n; i++) b[i] = 0; }

static int esperar(int p, uint32_t reg, uint32_t bits, int puestos, uint32_t tics) {
    uint32_t fin = timer_tics() + tics;
    for (;;) {
        uint32_t v = plee(p, reg) & bits;
        if (puestos ? v == bits : v == 0) return 0;
        if (timer_tics() > fin) return -1;
    }
}

static void parar(int p) {
    puerto_activo = -1;
    pescribe(p, P_CMD, plee(p, P_CMD) & ~1u);            /* ST = 0 */
    esperar(p, P_CMD, 1u << 15, 0, 60);                  /* CR libre */
    pescribe(p, P_CMD, plee(p, P_CMD) & ~(1u << 4));     /* FRE = 0 */
    esperar(p, P_CMD, 1u << 14, 0, 60);                  /* FR libre */
}

static int arrancar(int p) {
    parar(p);
    puerto_activo = p;
    ceros(lista, sizeof(lista)); ceros(recibidos, sizeof(recibidos));
    pescribe(p, P_CLB, (uint32_t)lista); pescribe(p, P_CLBU, 0);
    pescribe(p, P_FB, (uint32_t)recibidos); pescribe(p, P_FBU, 0);
    pescribe(p, P_SERR, 0xFFFFFFFFu);
    pescribe(p, P_IS, 0xFFFFFFFFu);
    pescribe(p, P_IE, 0);                                /* sin interrupciones: miramos nosotros */
    pescribe(p, P_CMD, plee(p, P_CMD) | (1u << 4));      /* FRE */
    pescribe(p, P_CMD, plee(p, P_CMD) | 1u);             /* ST */
    return 0;
}

/* Manda una orden de LECTURA (del disco a la memoria) y espera. 0 = bien. */
static int orden_lectura_n(int p, uint8_t cmd, uint32_t lba, uint32_t n, uint8_t *destino) {
    if (esperar(p, P_TFD, 0x88, 0, 100) != 0) return -1;     /* BSY y DRQ libres */
    ceros(&tab, sizeof(tab));
    lista[0].dw0 = 5u | (1u << 16);                           /* 5 dwords de FIS, W=0 (leer), 1 descriptor */
    lista[0].prdbc = 0;
    lista[0].ctba = (uint32_t)&tab; lista[0].ctbau = 0;
    tab.prdt[0].dba = (uint32_t)destino; tab.prdt[0].dbau = 0;
    tab.prdt[0].dbc = n * 512 - 1;                            /* n sectores de 512 bytes */
    tab.cfis[0] = 0x27; tab.cfis[1] = 0x80; tab.cfis[2] = cmd;
    tab.cfis[4] = (uint8_t)lba; tab.cfis[5] = (uint8_t)(lba >> 8); tab.cfis[6] = (uint8_t)(lba >> 16);
    tab.cfis[7] = 0x40;                                       /* modo LBA */
    tab.cfis[8] = (uint8_t)(lba >> 24);
    tab.cfis[12] = (uint8_t)n;                                /* cuántos sectores */
    pescribe(p, P_IS, 0xFFFFFFFFu);
    pescribe(p, P_CI, 1);
    uint32_t fin = timer_tics() + 300;
    while (plee(p, P_CI) & 1) {
        if (plee(p, P_IS) & (1u << 30)) return -2;           /* error del disco */
        if (timer_tics() > fin) return -3;
    }
    if ((plee(p, P_IS) & (1u << 30)) || (plee(p, P_TFD) & 1)) return -2;
    return 0;
}

static int orden_lectura(int p, uint8_t cmd, uint32_t lba, uint8_t *destino) {
    return orden_lectura_n(p, cmd, lba, 1, destino);
}

static void texto_id(const uint16_t *id, int desde, int palabras, char *sal) {
    int n = 0;
    for (int i = 0; i < palabras; i++) { sal[n++] = (char)(id[desde + i] >> 8); sal[n++] = (char)(id[desde + i] & 0xFF); }
    sal[n] = 0;
    while (n > 0 && sal[n - 1] == ' ') sal[--n] = 0;
}

static void tamano(uint32_t mb) {
    if (mb >= 10240) { kprint_dec(mb / 1024); kprint(" GB"); }
    else { kprint_dec(mb); kprint(" MB"); }
}

static uint32_t u32(const uint8_t *b) { return b[0] | (b[1] << 8) | (b[2] << 16) | ((uint32_t)b[3] << 24); }

static const char *tipo_mbr(uint8_t t) {
    switch (t) {
    case 0x83: return "Linux";
    case 0x82: return "Linux swap";
    case 0x8E: return "Linux LVM";
    case 0x07: return "NTFS (Windows)";
    case 0x0B: case 0x0C: return "FAT32";
    case 0x05: case 0x0F: return "extendida";
    case 0x27: return "recuperacion de Windows";
    case 0xEF: return "EFI";
    default:   return "otra";
    }
}

static const char *tipo_gpt(uint32_t g) {
    switch (g) {
    case 0x0FC63DAFu: return "Linux";
    case 0x0657FD6Du: return "Linux swap";
    case 0xE6D6D379u: return "Linux LVM";
    case 0xC12A7328u: return "EFI";
    case 0x21686148u: return "arranque BIOS";
    case 0xEBD0A0A2u: return "datos de Windows";
    case 0xE3C9E316u: return "reservada de Windows";
    case 0xDE94BBA4u: return "recuperacion de Windows";
    default:          return "otra";
    }
}

static void apuntar(uint32_t inicio, uint32_t sectores, int es_linux) {
    if (nparts >= 16) return;
    parts[nparts].disco = disco_actual; parts[nparts].inicio = inicio;
    parts[nparts].sectores = sectores; parts[nparts].es_linux = es_linux;
    nparts++;
}

static void particion(int n, const char *tipo, uint32_t sectores) {
    kprint("      "); kprint_dec((uint32_t)n); kprint(": "); kprint(tipo); kprint(", "); tamano((sectores + 1024) / 2048); kputc('\n');
}

static int leer_gpt(int p) {
    if (orden_lectura(p, 0x25, 1, buf) != 0) return 0;
    if (!(buf[0] == 'E' && buf[1] == 'F' && buf[2] == 'I' && buf[3] == ' ' && buf[4] == 'P')) return 0;
    uint32_t lba = u32(buf + 72), num = u32(buf + 80), tam = u32(buf + 84);
    if (tam < 128 || tam > 512 || num == 0) return 0;
    kprint("    Tabla GPT\n");
    int n = 0;
    uint32_t por_sector = 512 / tam, mirar = num < 32 ? num : 32;     /* las 32 primeras bastan */
    for (uint32_t i = 0; i < mirar; i++) {
        if (i % por_sector == 0 && orden_lectura(p, 0x25, lba + i / por_sector, entradas) != 0) break;
        const uint8_t *e = entradas + (i % por_sector) * tam;
        uint32_t tipo = u32(e);
        if (!tipo && !u32(e + 4)) continue;
        uint32_t ini = u32(e + 32), fin = u32(e + 40);
        apuntar(ini, fin >= ini ? fin - ini + 1 : 0, tipo == 0x0FC63DAFu);
        if (++n <= 8) particion(n, tipo_gpt(tipo), fin >= ini ? fin - ini + 1 : 0);
    }
    if (n > 8) { kprint("      … y "); kprint_dec((uint32_t)(n - 8)); kprint(" mas\n"); }
    if (!n) kprint("      (sin particiones)\n");
    return 1;
}

static void leer_tabla(int p) {
    if (orden_lectura(p, 0x25, 0, buf) != 0) { kprint("    no puedo leer el sector 0\n"); return; }
    if (buf[510] != 0x55 || buf[511] != 0xAA) { kprint("    sin tabla de particiones\n"); return; }
    if (buf[446 + 4] == 0xEE && leer_gpt(p)) return;           /* MBR protector: es GPT */
    if (orden_lectura(p, 0x25, 0, buf) != 0) return;
    kprint("    Tabla MBR\n");
    int n = 0;
    for (int i = 0; i < 4; i++) {
        const uint8_t *e = buf + 446 + 16 * i;
        if (!e[4]) continue;
        apuntar(u32(e + 8), u32(e + 12), e[4] == 0x83);
        particion(i + 1, tipo_mbr(e[4]), u32(e + 12));
        n++;
    }
    if (!n) kprint("      (sin particiones)\n");
}

static int mirar_puerto(int p) {
    uint32_t ssts = plee(p, P_SSTS);
    if ((ssts & 0xF) != 3) return 0;                             /* no hay nada enchufado */
    kprint("  Puerto "); kprint_dec((uint32_t)p); kprint(": ");
    if (((ssts >> 8) & 0xF) != 1) { kprint("aparato dormido (no lo despierto)\n"); return 0; }
    uint32_t sig = plee(p, P_SIG);
    if (sig == SIG_ATAPI) { kprint("lector de CD/DVD (no lo leo)\n"); return 0; }
    if (sig != SIG_ATA) { kprint("otro aparato SATA\n"); return 0; }
    arrancar(p);
    uint16_t id[256];
    if (orden_lectura(p, 0xEC, 0, (uint8_t *)id) != 0) { kprint("disco que no contesta\n"); parar(p); return 0; }
    char modelo[41];
    texto_id(id, 27, 20, modelo);
    uint32_t lo, hi;
    if (id[83] & (1u << 10)) { lo = id[100] | ((uint32_t)id[101] << 16); hi = id[102] | ((uint32_t)id[103] << 16); }
    else { lo = id[60] | ((uint32_t)id[61] << 16); hi = 0; }
    kprint("disco "); kprint(modelo); kprint(", "); tamano((hi << 21) | (lo >> 11)); kputc('\n');
    if (ndiscos < 4) {
        disco_actual = ndiscos;
        discos[ndiscos].puerto = p; discos[ndiscos].mb = (hi << 21) | (lo >> 11);
        for (int i = 0; i < 41; i++) discos[ndiscos].modelo[i] = modelo[i];
        ndiscos++;
    }
    leer_tabla(p);
    parar(p);
    return 1;
}

int ahci_leer(int disco, uint32_t lba, uint32_t n, void *destino) {
    if (disco < 0 || disco >= ndiscos || n == 0 || n > 16) return -1;
    int p = discos[disco].puerto;
    if (puerto_activo != p) {
        if (puerto_activo >= 0) parar(puerto_activo);
        arrancar(p);
    }
    return orden_lectura_n(p, 0x25, lba, n, (uint8_t *)destino);
}

int ahci_particion(int i, int *disco, uint32_t *inicio, uint32_t *sectores, int *es_linux) {
    if (i < 0 || i >= nparts) return 0;
    *disco = parts[i].disco; *inicio = parts[i].inicio; *sectores = parts[i].sectores; *es_linux = parts[i].es_linux;
    return 1;
}

int ahci_num_discos(void) { return ndiscos; }

void ahci_resumen(void) {
    if (!ndiscos) { kprint("No hay discos SATA (AHCI)\n"); return; }
    for (int d = 0; d < ndiscos; d++) {
        kprint("Disco "); kprint_dec((uint32_t)d); kprint(": "); kprint(discos[d].modelo); kprint(", ");
        tamano(discos[d].mb); kputc('\n');
        for (int i = 0; i < nparts; i++) if (parts[i].disco == d) {
            kprint("  particion en el sector "); kprint_dec(parts[i].inicio); kprint(", ");
            tamano((parts[i].sectores + 1024) / 2048);
            kprint(parts[i].es_linux ? " (Linux)\n" : "\n");
        }
    }
}

void ahci_probar(void) {
    struct pci_disp d;
    if (!pci_buscar_clase(0x01, 0x06, &d)) {
        kprint("AHCI: no hay controlador SATA en modo AHCI\n");
        return;
    }
    uint32_t orden = pci_leer(d.bus, d.disp, d.func, 0x04);
    pci_escribir(d.bus, d.disp, d.func, 0x04, orden | 0x06);      /* memoria + bus master */
    abar = pci_leer(d.bus, d.disp, d.func, 0x24) & 0xFFFFF000u;   /* BAR5 */
    if (!abar) { kprint("AHCI: el controlador no tiene direccion\n"); return; }
    paginacion_mapear(abar, 0x1100);
    if ((lee(CAP2) & 1) && (lee(BOHC) & 1)) {                     /* la BIOS aún lo maneja: se lo pido */
        escribe(BOHC, lee(BOHC) | 2);
        uint32_t fin = timer_tics() + 200;
        while ((lee(BOHC) & 1) && timer_tics() < fin) { }
    }
    escribe(GHC, (lee(GHC) | (1u << 31)) & ~2u);                  /* modo AHCI, sin interrupciones */
    uint32_t vs = lee(VS), pi = lee(PI);
    kprint("AHCI: controlador ");
    kprint_dec(vs >> 16); kputc('.'); kprint_dec((vs >> 8) & 0xFF);
    kprint(", "); kprint_dec((lee(CAP) & 0x1F) + 1); kprint(" puertos\n");
    int discos = 0;
    for (int p = 0; p < 32; p++) if (pi & (1u << p)) discos += mirar_puerto(p);
    if (!discos) { kprint("AHCI: no he encontrado discos\n"); return; }
    kprint("AHCI OK (solo lectura: "); kprint_dec((uint32_t)discos); kprint(discos == 1 ? " disco)\n" : " discos)\n");
}
"""



_EXT4_H = r"""/* ext4.h — leer el sistema de archivos de Linux (ext4): SOLO LECTURA */
#ifndef EXT4_H
#define EXT4_H
#include <stdint.h>
int ext4_montar(void);                                            /* busca una partición Linux con ext4; 1 = bien */
int ext4_listar(const char *ruta);                                /* escribe lo que hay; nº de entradas o -1 */
int ext4_cat(const char *ruta, uint32_t max);                     /* escribe el archivo (hasta max bytes); 0 = bien */
int ext4_leer(const char *ruta, void *buf, uint32_t max, uint32_t *tam);   /* lo copia en buf; 0 = bien */
int ext4_existe(const char *ruta);                                /* 1 archivo, 2 carpeta, 0 no está */
int ext4_nombres(const char *ruta, char nombres[][32], int max);   /* nombres de una carpeta */
void ext4_probar(void);
#endif
"""

_EXT4_C = r"""/* ext4.c — sistema de archivos de Linux (ext4) de SOLO LECTURA: superbloque, descriptores de grupo (también de 64
   bits), inodos, extents (y bloques directos de los ext2/3 viejos) y carpetas. Lee por el driver AHCI: nunca escribe. */
#include <stdint.h>
#include "ext4.h"
#include "ahci.h"
#include "consola.h"
#include "memoria.h"

#define MAX_INODO 256
static int disco = -1, montado = 0;
static uint32_t inicio = 0, tam_bloque = 0, spb = 0, ipg = 0, tam_inodo = 0, tam_desc = 32, primer = 0;
static uint8_t sb[1024];
static char volumen[17];

static uint16_t u16(const uint8_t *b) { return (uint16_t)(b[0] | (b[1] << 8)); }
static uint32_t u32(const uint8_t *b) { return b[0] | (b[1] << 8) | (b[2] << 16) | ((uint32_t)b[3] << 24); }

static int leer_bloque(uint32_t b, uint8_t *buf) {
    if (tam_bloque > 4096) {                                   /* bloques grandes: a trozos de 8 sectores */
        for (uint32_t i = 0; i < spb; i += 8)
            if (ahci_leer(disco, inicio + b * spb + i, 8, buf + i * 512) != 0) return -1;
        return 0;
    }
    return ahci_leer(disco, inicio + b * spb, spb, buf);
}

static int leer_inodo(uint32_t n, uint8_t *ino) {
    if (n == 0) return -1;
    uint32_t grupo = (n - 1) / ipg, idx = (n - 1) % ipg;
    uint8_t *b = kmalloc(tam_bloque);
    if (!b) return -1;
    uint32_t off = grupo * tam_desc;
    if (leer_bloque(primer + 1 + off / tam_bloque, b) != 0) { kfree(b); return -1; }
    const uint8_t *d = b + off % tam_bloque;
    uint32_t tabla = u32(d + 8);
    if (tam_desc >= 64 && u32(d + 0x28)) { kfree(b); return -1; }   /* tabla más allá de 16 TB: no */
    uint32_t pos = idx * tam_inodo;
    if (leer_bloque(tabla + pos / tam_bloque, b) != 0) { kfree(b); return -1; }
    uint32_t copiar = tam_inodo < MAX_INODO ? tam_inodo : MAX_INODO;
    for (uint32_t i = 0; i < copiar; i++) ino[i] = b[pos % tam_bloque + i];
    kfree(b);
    return 0;
}

/* bloque físico del bloque lógico lb de un árbol de extents (0 = hueco) */
static uint32_t en_extents(const uint8_t *nodo, uint32_t lb, int vueltas) {
    if (u16(nodo) != 0xF30A || vueltas > 5) return 0;
    uint16_t n = u16(nodo + 2), prof = u16(nodo + 6);
    if (prof == 0) {
        for (uint16_t i = 0; i < n; i++) {
            const uint8_t *e = nodo + 12 + 12 * i;
            uint32_t ini = u32(e), largo = u16(e + 4);
            int sin_escribir = largo > 32768;
            if (sin_escribir) largo -= 32768;
            if (lb >= ini && lb < ini + largo) {
                if (sin_escribir || u16(e + 6)) return 0;   /* reservado sin datos (o más allá de 16 TB) */
                return u32(e + 8) + (lb - ini);
            }
        }
        return 0;
    }
    const uint8_t *elegido = 0;
    for (uint16_t i = 0; i < n; i++) {
        const uint8_t *e = nodo + 12 + 12 * i;
        if (u32(e) <= lb) elegido = e; else break;
    }
    if (!elegido || u16(elegido + 8)) return 0;
    uint8_t *b = kmalloc(tam_bloque);
    if (!b) return 0;
    uint32_t r = 0;
    if (leer_bloque(u32(elegido + 4), b) == 0) r = en_extents(b, lb, vueltas + 1);
    kfree(b);
    return r;
}

static uint32_t bloque_de(const uint8_t *ino, uint32_t lb) {
    uint32_t flags = u32(ino + 32);
    const uint8_t *iblock = ino + 40;
    if (flags & 0x80000) return en_extents(iblock, lb, 0);      /* extents (lo normal en ext4) */
    if (lb < 12) return u32(iblock + 4 * lb);                   /* ext2/3: directos */
    lb -= 12;
    uint32_t por = tam_bloque / 4;
    if (lb < por && u32(iblock + 48)) {                         /* indirecto simple */
        uint8_t *b = kmalloc(tam_bloque);
        if (!b) return 0;
        uint32_t r = leer_bloque(u32(iblock + 48), b) == 0 ? u32(b + 4 * lb) : 0;
        kfree(b);
        return r;
    }
    return 0;
}

static uint32_t tam_de(const uint8_t *ino) { return u32(ino + 4); }   /* hasta 4 GB: suficiente aquí */
static int es_carpeta(const uint8_t *ino) { return (u16(ino) & 0xF000) == 0x4000; }

static void escribir_texto(const uint8_t *t, uint32_t n);

/* recorre una carpeta; si nombre != 0 devuelve el inodo de esa entrada; si no, las escribe */
static uint32_t carpeta(const uint8_t *ino, const char *nombre, int largo, int escribir, int *cuantas) {
    uint32_t total = tam_de(ino), bloques = (total + tam_bloque - 1) / tam_bloque, col = 0;
    uint8_t *b = kmalloc(tam_bloque);
    if (!b) return 0;
    for (uint32_t lb = 0; lb < bloques; lb++) {
        uint32_t fis = bloque_de(ino, lb);
        if (!fis || leer_bloque(fis, b) != 0) continue;
        uint32_t pos = 0;
        while (pos + 8 <= tam_bloque) {
            const uint8_t *e = b + pos;
            uint32_t num = u32(e);
            uint16_t rec = u16(e + 4);
            uint8_t nl = e[6], tipo = e[7];
            if (rec < 8 || pos + rec > tam_bloque) break;
            if (num && nl && nl <= rec - 8) {
                const char *nm = (const char *)e + 8;
                if (nombre) {
                    if (nl == largo) {
                        int igual = 1;
                        for (int i = 0; i < largo; i++) if (nm[i] != nombre[i]) { igual = 0; break; }
                        if (igual) { kfree(b); return num; }
                    }
                } else if (!(nl == 1 && nm[0] == '.') && !(nl == 2 && nm[0] == '.' && nm[1] == '.')) {
                    if (cuantas) (*cuantas)++;
                    if (escribir) {
                        if (col + nl + 3 > 76) { kputc('\n'); col = 0; }
                        kprint("  ");
                        escribir_texto((const uint8_t *)nm, nl);     /* «Música» bien, no «M├║sica» */
                        if (tipo == 2) kputc('/');
                        else if (tipo == 7) kputc('@');              /* enlace (como bin -> usr/bin) */
                        col += nl + 3;
                    }
                }
            }
            pos += rec;
        }
    }
    if (escribir && col) kputc('\n');
    kfree(b);
    return 0;
}

/* el único nombre de la carpeta que empieza por «ini» (0 si no hay o hay varios) */
static uint32_t por_prefijo(const uint8_t *ino, const char *ini, int largo) {
    uint32_t total = tam_de(ino), bloques = (total + tam_bloque - 1) / tam_bloque, hallado = 0;
    int cuantos = 0;
    uint8_t *b = kmalloc(tam_bloque);
    if (!b) return 0;
    for (uint32_t lb = 0; lb < bloques && cuantos < 2; lb++) {
        uint32_t fis = bloque_de(ino, lb);
        if (!fis || leer_bloque(fis, b) != 0) continue;
        uint32_t pos = 0;
        while (pos + 8 <= tam_bloque) {
            const uint8_t *e = b + pos;
            uint16_t rec = u16(e + 4);
            uint8_t nl = e[6];
            if (rec < 8 || pos + rec > tam_bloque) break;
            if (u32(e) && nl >= largo && nl <= rec - 8) {
                int si = 1;
                for (int i = 0; i < largo; i++) if (e[8 + i] != (uint8_t)ini[i]) { si = 0; break; }
                if (si) { cuantos++; hallado = u32(e); }
            }
            pos += rec;
        }
    }
    kfree(b);
    return cuantos == 1 ? hallado : 0;
}

static uint32_t buscar(const char *ruta, uint8_t *ino) {
    uint32_t n = 2;                                             /* la raíz «/» es siempre el inodo 2 */
    if (leer_inodo(n, ino) != 0) return 0;
    const char *p = ruta;
    while (*p) {
        while (*p == '/') p++;
        if (!*p) break;
        const char *ini = p;
        while (*p && *p != '/') p++;
        int largo = (int)(p - ini);
        if (!es_carpeta(ino)) return 0;
        n = carpeta(ino, ini, largo, 0, 0);
        if (!n) n = por_prefijo(ino, ini, largo);              /* «notas» → notas.txt si es el único */
        if (!n || leer_inodo(n, ino) != 0) return 0;
    }
    return n;
}

int ext4_montar(void) {
    if (montado) return 1;
    int d, l; uint32_t ini, sec;
    for (int i = 0; ahci_particion(i, &d, &ini, &sec, &l); i++) {
        if (!l) continue;
        if (ahci_leer(d, ini + 2, 2, sb) != 0) continue;      /* el superbloque empieza en el byte 1024 */
        if (u16(sb + 56) != 0xEF53) continue;
        uint32_t log = u32(sb + 24);
        if (log > 4) continue;                                  /* bloques de 1 a 16 KB */
        disco = d; inicio = ini;
        tam_bloque = 1024u << log; spb = tam_bloque / 512;
        ipg = u32(sb + 40); primer = u32(sb + 20);
        tam_inodo = u32(sb + 76) >= 1 ? u16(sb + 88) : 128;
        tam_desc = (u32(sb + 96) & 0x80) ? u16(sb + 254) : 32;  /* 64 bits */
        if (tam_desc < 32) tam_desc = 32;
        if (!ipg || tam_inodo < 128) continue;
        for (int k = 0; k < 16; k++) volumen[k] = (char)sb[120 + k];
        volumen[16] = 0;
        montado = 1;
        uint32_t bloques = u32(sb + 4);
        kprint("EXT4: particion Linux");
        if (volumen[0]) { kprint(" \""); kprint(volumen); kputc('"'); }
        kprint(", ");
        uint32_t mb = bloques / (1048576 / tam_bloque);
        if (mb >= 10240) { kprint_dec(mb / 1024); kprint(" GB"); } else { kprint_dec(mb); kprint(" MB"); }
        kprint(", bloques de "); kprint_dec(tam_bloque / 1024); kprint(" KB (solo lectura)\n");
        return 1;
    }
    return 0;
}

int ext4_existe(const char *ruta) {
    uint8_t ino[MAX_INODO];
    if (!ext4_montar() || !buscar(ruta, ino)) return 0;
    return es_carpeta(ino) ? 2 : 1;
}

int ext4_listar(const char *ruta) {
    uint8_t ino[MAX_INODO];
    if (!ext4_montar()) { kprint("No hay ningun disco con ext4\n"); return -1; }
    if (!buscar(ruta, ino)) { kprint("No existe: "); kprint(ruta); kputc('\n'); return -1; }
    if (!es_carpeta(ino)) { kprint(ruta); kprint(" es un archivo de "); kprint_dec(tam_de(ino)); kprint(" bytes\n"); return 0; }
    int n = 0;
    carpeta(ino, 0, 0, 1, &n);
    return n;
}

int ext4_leer(const char *ruta, void *destino, uint32_t max, uint32_t *tam) {
    uint8_t ino[MAX_INODO];
    if (!ext4_montar() || !buscar(ruta, ino) || es_carpeta(ino)) return -1;
    uint32_t total = tam_de(ino), copiado = 0;
    if (tam) *tam = total;
    if (total > max) total = max;
    uint8_t *b = kmalloc(tam_bloque), *o = destino;
    if (!b) return -1;
    for (uint32_t lb = 0; copiado < total; lb++) {
        uint32_t fis = bloque_de(ino, lb), n = total - copiado;
        if (n > tam_bloque) n = tam_bloque;
        if (fis) { if (leer_bloque(fis, b) != 0) { kfree(b); return -1; } }
        else for (uint32_t i = 0; i < tam_bloque; i++) b[i] = 0;   /* hueco: ceros */
        for (uint32_t i = 0; i < n; i++) o[copiado + i] = b[i];
        copiado += n;
    }
    kfree(b);
    return 0;
}

/* letras con tilde (UTF-8) → la tabla de la pantalla de texto (página 437) */
static void escribir_texto(const uint8_t *t, uint32_t n) {
    for (uint32_t i = 0; i < n; i++) {
        uint8_t c = t[i];
        if (c == 0xC3 && i + 1 < n) {
            uint8_t s = t[++i];
            const char *de = "\xA1\xA9\xAD\xB3\xBA\xB1\x91\xBC\x81\x89\x8D\x93\x9A";
            const char *a  = "\xA0\x82\xA1\xA2\xA3\xA4\xA5\x81\x41\x90\x49\x4F\x55";
            char r = '?';
            for (int k = 0; de[k]; k++) if ((uint8_t)de[k] == s) { r = a[k]; break; }
            kputc(r);
        } else if (c == 0xC2 && i + 1 < n) {
            uint8_t s = t[++i];
            kputc(s == 0xBF ? (char)0xA8 : s == 0xA1 ? (char)0xAD : '?');
        } else if (c == '\n' || c == '\t' || (c >= 32 && c < 127)) {
            kputc(c == '\t' ? ' ' : (char)c);
        } else if (c >= 0x80) {
            if ((c & 0xC0) != 0x80) kputc('?');               /* otras letras raras: una ? por letra */
        } else {
            kputc('.');
        }
    }
}

int ext4_cat(const char *ruta, uint32_t max) {
    uint8_t ino[MAX_INODO];
    if (!ext4_montar()) { kprint("No hay ningun disco con ext4\n"); return -1; }
    if (!buscar(ruta, ino)) { kprint("No existe: "); kprint(ruta); kputc('\n'); return -1; }
    if (es_carpeta(ino)) { kprint(ruta); kprint(" es una carpeta (usa ls)\n"); return -1; }
    uint32_t total = tam_de(ino);
    uint32_t n = total < max ? total : max;
    uint8_t *t = kmalloc(n + 1);
    if (!t) { kprint("Sin memoria para leerlo\n"); return -1; }
    if (ext4_leer(ruta, t, n, 0) != 0) { kfree(t); kprint("No pude leerlo\n"); return -1; }
    escribir_texto(t, n);
    if (n && t[n - 1] != '\n') kputc('\n');
    if (total > n) { kprint("... (y "); kprint_dec(total - n); kprint(" bytes mas)\n"); }
    kfree(t);
    return 0;
}

/* los nombres de una carpeta (sin «.» ni «..»); devuelve cuántos ha puesto */
int ext4_nombres(const char *ruta, char nombres[][32], int max) {
    uint8_t ino[MAX_INODO];
    if (!ext4_montar() || !buscar(ruta, ino) || !es_carpeta(ino)) return 0;
    uint32_t total = tam_de(ino), bloques = (total + tam_bloque - 1) / tam_bloque;
    int n = 0;
    uint8_t *b = kmalloc(tam_bloque);
    if (!b) return 0;
    for (uint32_t lb = 0; lb < bloques && n < max; lb++) {
        uint32_t fis = bloque_de(ino, lb);
        if (!fis || leer_bloque(fis, b) != 0) continue;
        uint32_t pos = 0;
        while (pos + 8 <= tam_bloque && n < max) {
            const uint8_t *e = b + pos;
            uint16_t rec = u16(e + 4);
            uint8_t nl = e[6];
            if (rec < 8 || pos + rec > tam_bloque) break;
            if (u32(e) && nl && nl < 32 && nl <= rec - 8 && !(nl == 1 && e[8] == '.') &&
                !(nl == 2 && e[8] == '.' && e[9] == '.')) {
                for (int i = 0; i < nl; i++) nombres[n][i] = (char)e[8 + i];
                nombres[n][nl] = 0;
                n++;
            }
            pos += rec;
        }
    }
    kfree(b);
    return n;
}

void ext4_probar(void) {
    if (!ext4_montar()) { kprint("EXT4: no he encontrado ninguna particion Linux con ext4\n"); return; }
    kprint("Carpeta /:\n");
    if (ext4_listar("/") < 0) return;
    if (ext4_existe("/kira.txt") == 1) {                       /* el disco de pruebas de QEMU */
        kprint("/kira.txt dice: ");
        ext4_cat("/kira.txt", 200);
    } else if (ext4_existe("/home") == 2) {                   /* tu Xubuntu */
        kprint("Carpeta /home:\n");
        ext4_listar("/home");
    }
    kprint("EXT4 OK (solo lectura)\n");
}
"""

_CONSOLA2_H = r"""/* consola.h (v2) — pantalla VGA y puerto serie; además borrar, limpiar y leer del serie */
#ifndef CONSOLA_H
#define CONSOLA_H
#include <stdint.h>

void consola_init(void);
void kputc(char c);
void kprint(const char *s);
void kprint_dec(uint32_t n);
void kprint_hex(uint32_t n);
int serie_leer(void);            /* un carácter del puerto serie o -1 (en un portátil sin COM1, siempre -1) */
void consola_limpiar(void);

#endif
"""

_CONSOLA2_C = r"""/* consola.c (v2) — pantalla VGA de texto + puerto serie COM1 (lo que lee el taller para saber si funciona) */
#include <stddef.h>
#include "consola.h"
#include "io.h"

#define COM1 0x3F8
static volatile uint16_t *const VGA = (uint16_t *)0xB8000;
static size_t fila = 0, col = 0;
static const uint8_t COLOR = 0x0F;            /* blanco sobre negro */

static int serie_ok = 0;                      /* en un portátil de verdad puede no haber puerto serie */

static void serie_init(void) {
    outb(COM1 + 7, 0xAE);    /* registro de prueba: si no devuelve lo escrito, no hay puerto serie */
    if (inb(COM1 + 7) != 0xAE) { serie_ok = 0; return; }
    serie_ok = 1;
    outb(COM1 + 1, 0x00);    /* sin interrupciones */
    outb(COM1 + 3, 0x80);    /* DLAB para poner la velocidad */
    outb(COM1 + 0, 0x03);    /* 38400 baudios */
    outb(COM1 + 1, 0x00);
    outb(COM1 + 3, 0x03);    /* 8 bits, sin paridad, 1 de parada */
    outb(COM1 + 2, 0xC7);    /* FIFO */
    outb(COM1 + 4, 0x0B);
}

static void serie_putc(char c) {
    if (!serie_ok) return;
    for (int i = 0; i < 100000 && (inb(COM1 + 5) & 0x20) == 0; i++) { }   /* nunca esperar para siempre */
    outb(COM1, (uint8_t)c);
}

static void vga_bajar(void) {
    for (size_t i = 0; i < 80 * 24; i++) VGA[i] = VGA[i + 80];
    for (size_t i = 80 * 24; i < 80 * 25; i++) VGA[i] = (uint16_t)' ' | (uint16_t)COLOR << 8;
    fila = 24;
}

static void vga_putc(char c) {
    if (c == '\n') { col = 0; if (++fila == 25) vga_bajar(); return; }
    if (c == '\b') {                                    /* borrar la letra de antes */
        if (col) col--; else if (fila) { fila--; col = 79; }
        VGA[fila * 80 + col] = (uint16_t)' ' | (uint16_t)COLOR << 8;
        return;
    }
    VGA[fila * 80 + col] = (uint16_t)(uint8_t)c | (uint16_t)COLOR << 8;
    if (++col == 80) { col = 0; if (++fila == 25) vga_bajar(); }
}

void consola_init(void) {
    serie_init();
    for (size_t i = 0; i < 80 * 25; i++) VGA[i] = (uint16_t)' ' | (uint16_t)COLOR << 8;
    fila = col = 0;
}

void kputc(char c) {
    vga_putc(c);
    if (c == '\b') { serie_putc('\b'); serie_putc(' '); }
    serie_putc(c);
}

void kprint(const char *s) { while (*s) kputc(*s++); }

void kprint_dec(uint32_t n) {
    char b[11]; int i = 0;
    if (n == 0) { kputc('0'); return; }
    while (n) { b[i++] = (char)('0' + n % 10); n /= 10; }
    while (i) kputc(b[--i]);
}

void kprint_hex(uint32_t n) {
    const char *d = "0123456789ABCDEF";
    kprint("0x");
    for (int s = 28; s >= 0; s -= 4) kputc(d[(n >> s) & 0xF]);
}

int serie_leer(void) {
    if (!serie_ok) return -1;
    if (inb(COM1 + 5) & 1) return inb(COM1);
    return -1;
}

void consola_limpiar(void) {
    for (size_t i = 0; i < 80 * 25; i++) VGA[i] = (uint16_t)' ' | (uint16_t)COLOR << 8;
    fila = col = 0;
}
"""

_TECLADO_H = r"""/* teclado.h — teclado PS/2 con memoria: la consola lee las teclas de aquí */
#ifndef TECLADO_H
#define TECLADO_H
void teclado_init(void);
int teclado_leer(void);          /* la siguiente tecla o -1 si no hay */
void teclado_eco(int si);        /* 1 = la escribe en pantalla al pulsarla (como antes); 0 = la consola decide */
#endif
"""

_TECLADO2_C = r"""/* teclado.c (v2) — teclado PS/2 (IRQ 1) en español: guarda las teclas en un búfer circular, entiende Mayúsculas
   (/ : ; _ ? ! = …) y Bloq Mayús. Esc reinicia el ordenador (para volver a tu Xubuntu desde el USB). */
#include "io.h"
#include "idt.h"
#include "consola.h"
#include "teclado.h"

static const char MAPA[128] = {
    0, 27, '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '\'', 0, '\b',
    '\t', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '`', '+', '\n',
    0, 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 0, 0, 0,
    0, '<', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '-', 0,
    '*', 0, ' '
};
static const char MAPA_MAYUS[128] = {
    0, 27, '!', '"', '#', '$', '%', '&', '/', '(', ')', '=', '?', 0, '\b',
    '\t', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '^', '*', '\n',
    0, 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 0, 0, 0,
    0, '>', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ';', ':', '_', 0,
    '*', 0, ' '
};
#define TAM 128
static volatile char bufer[TAM];
static volatile int cabeza = 0, cola = 0;
static int mayus = 0, bloq = 0, eco = 1;

void teclado_eco(int si) { eco = si; }

int teclado_leer(void) {
    if (cola == cabeza) return -1;
    char c = bufer[cola];
    cola = (cola + 1) % TAM;
    return (unsigned char)c;
}

static void teclado_irq(struct registros *r) {
    (void)r;
    uint8_t sc = inb(0x60);
    if (sc == 0x2A || sc == 0x36) { mayus = 1; return; }      /* shift pulsado */
    if (sc == 0xAA || sc == 0xB6) { mayus = 0; return; }      /* shift soltado */
    if (sc == 0x3A) { bloq = !bloq; return; }                 /* Bloq Mayús */
    if (sc == 0x01) {                                         /* Esc: reiniciar */
        kprint("\nReiniciando...\n");
        for (int i = 0; i < 100000 && (inb(0x64) & 0x02); i++) { }
        outb(0x64, 0xFE);
        return;
    }
    if (sc & 0x80) return;                                    /* tecla soltada */
    if (sc >= 128) return;
    char c = mayus ? MAPA_MAYUS[sc] : MAPA[sc];
    if (!c) return;
    if (bloq && !mayus && c >= 'a' && c <= 'z') c = (char)(c - 32);
    int sig = (cabeza + 1) % TAM;
    if (sig != cola) { bufer[cabeza] = c; cabeza = sig; }     /* si el búfer está lleno, se pierde la tecla */
    if (eco) kputc(c);
}

void teclado_init(void) {
    idt_poner_manejador(33, teclado_irq);
    kprint("Teclado OK\n");
}
"""

_SHELL_H = r"""/* shell.h — la consola propia del kernel: «kira>» */
#ifndef SHELL_H
#define SHELL_H
typedef void (*orden_f)(const char *args);
void shell_init(const char *version);
void shell_orden(const char *nombre, const char *ayuda, orden_f f);   /* las etapas siguientes añaden las suyas */
void shell_ruta(const char *arg, char *sal, int max);                /* une la carpeta actual con lo escrito */
void shell_bucle(void);                                              /* lee órdenes para siempre */
#endif
"""

_SHELL_C = r"""/* shell.c — consola propia del kernel de Kira. Lee del teclado (y del puerto serie, para probarla en QEMU),
   permite borrar con la tecla de retroceso y ejecuta órdenes: ayuda, ls, cd, cat, aparatos, discos, memoria… */
#include <stdint.h>
#include "shell.h"
#include "consola.h"
#include "teclado.h"
#include "timer.h"
#include "memoria.h"
#include "pci.h"
#include "ahci.h"
#include "ext4.h"
#include "io.h"

#define MAX_ORDENES 24
#define MAX_LINEA 160
struct orden { const char *nombre, *ayuda; orden_f f; };
static struct orden ordenes[MAX_ORDENES];
static int nordenes = 0;
static char actual[128] = "/";
static const char *version_k = "";

static int igual(const char *a, const char *b) {
    while (*a && *a == *b) { a++; b++; }
    return *a == *b;
}
static int largo(const char *s) { int n = 0; while (s[n]) n++; return n; }

void shell_orden(const char *nombre, const char *ayuda, orden_f f) {
    for (int i = 0; i < nordenes; i++) if (igual(ordenes[i].nombre, nombre)) { ordenes[i].ayuda = ayuda; ordenes[i].f = f; return; }
    if (nordenes < MAX_ORDENES) { ordenes[nordenes].nombre = nombre; ordenes[nordenes].ayuda = ayuda; ordenes[nordenes].f = f; nordenes++; }
}

/* «/home/papi» + «../x» → «/home/x»; quita «.» y «..» */
void shell_ruta(const char *arg, char *sal, int max) {
    char tmp[256];
    int n = 0;
    if (!arg || !*arg) arg = ".";
    if (arg[0] != '/') { for (int i = 0; actual[i] && n < 250; i++) tmp[n++] = actual[i]; if (n < 250) tmp[n++] = '/'; }
    for (int i = 0; arg[i] && n < 254; i++) tmp[n++] = arg[i];
    tmp[n] = 0;
    int pos = 0;
    sal[pos++] = '/';
    const char *p = tmp;
    while (*p) {
        while (*p == '/') p++;
        if (!*p) break;
        const char *ini = p;
        while (*p && *p != '/') p++;
        int l = (int)(p - ini);
        if (l == 1 && ini[0] == '.') continue;
        if (l == 2 && ini[0] == '.' && ini[1] == '.') {
            if (pos > 1) { pos--; while (pos > 1 && sal[pos - 1] != '/') pos--; if (pos > 1) pos--; }
            continue;
        }
        if (pos > 1 && pos < max - 1) sal[pos++] = '/';
        for (int i = 0; i < l && pos < max - 1; i++) sal[pos++] = ini[i];
    }
    sal[pos] = 0;
}

static void o_ayuda(const char *a) {
    (void)a;
    kprint("Ordenes:\n");
    for (int i = 0; i < nordenes; i++) {
        kprint("  "); kprint(ordenes[i].nombre);
        for (int k = largo(ordenes[i].nombre); k < 10; k++) kputc(' ');
        kprint(ordenes[i].ayuda); kputc('\n');
    }
    kprint("Las rutas pueden ser incompletas: \"cat notas\" abre notas.txt si es el unico que empieza asi.\n");
}
static void o_limpiar(const char *a) { (void)a; consola_limpiar(); }
static void o_eco(const char *a) { kprint(a); kputc('\n'); }
static void o_tiempo(const char *a) {
    (void)a;
    uint32_t s = timer_tics() / 100;
    kprint("Encendido hace "); kprint_dec(s / 60); kprint(" min "); kprint_dec(s % 60); kprint(" s\n");
}
static void o_memoria(const char *a) {
    (void)a;
    kprint("Memoria libre: "); kprint_dec(marcos_libres() / 256); kprint(" MB (en marcos de 4 KB)\n");
}
static void o_aparatos(const char *a) { (void)a; pci_listar(); }
static void o_discos(const char *a) { (void)a; ahci_resumen(); }
static void o_ls(const char *a) { char r[128]; shell_ruta(a, r, sizeof(r)); ext4_listar(r); }
static void o_cat(const char *a) {
    if (!*a) { kprint("Dime que archivo: cat <archivo>\n"); return; }
    char r[128]; shell_ruta(a, r, sizeof(r)); ext4_cat(r, 4000);
}
static void o_cd(const char *a) {
    char r[128]; shell_ruta(*a ? a : "/", r, sizeof(r));
    if (ext4_existe(r) != 2) { kprint("No es una carpeta: "); kprint(r); kputc('\n'); return; }
    for (int i = 0; i < 128; i++) { actual[i] = r[i]; if (!r[i]) break; }
}
static void o_pwd(const char *a) { (void)a; kprint(actual); kputc('\n'); }
static void o_version(const char *a) { (void)a; kprint("Kernel de Kira - "); kprint(version_k); kputc('\n'); }
static void o_reiniciar(const char *a) {
    (void)a;
    kprint("Reiniciando...\n");
    for (int i = 0; i < 100000 && (inb(0x64) & 0x02); i++) { }
    outb(0x64, 0xFE);
}

void shell_init(const char *version) {
    version_k = version;
    teclado_eco(0);
    shell_orden("ayuda", "lo que se puede hacer", o_ayuda);
    shell_orden("ls", "lo que hay en una carpeta (ls /home)", o_ls);
    shell_orden("cd", "entrar en una carpeta (cd /home/papi, cd ..)", o_cd);
    shell_orden("pwd", "en que carpeta estoy", o_pwd);
    shell_orden("cat", "ver un archivo de texto (cat notas.txt)", o_cat);
    shell_orden("aparatos", "los aparatos del ordenador (PCI)", o_aparatos);
    shell_orden("discos", "discos y particiones", o_discos);
    shell_orden("memoria", "memoria libre", o_memoria);
    shell_orden("tiempo", "cuanto llevo encendido", o_tiempo);
    shell_orden("eco", "repite lo que escribas", o_eco);
    shell_orden("limpiar", "borra la pantalla", o_limpiar);
    shell_orden("version", "que kernel es", o_version);
    shell_orden("reiniciar", "reinicia el ordenador (igual que Esc)", o_reiniciar);
}

static int leer_tecla(void) {
    for (;;) {
        int c = teclado_leer();
        if (c >= 0) return c;
        c = serie_leer();
        if (c >= 0) return c == '\r' ? '\n' : c;
        __asm__ volatile ("hlt");
    }
}

static void ejecutar(char *l) {
    while (*l == ' ') l++;
    if (!*l) return;
    char *args = l;
    while (*args && *args != ' ') args++;
    if (*args) { *args++ = 0; while (*args == ' ') args++; }
    else {                                       /* «ls/home» o «cd..»: la orden son las letras del principio */
        char *p = l;
        while ((*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z')) p++;
        if (*p && p > l) {
            static char resto[MAX_LINEA];
            int i = 0;
            for (char *q = p; *q && i < MAX_LINEA - 1; q++) resto[i++] = *q;
            resto[i] = 0;
            *p = 0;
            args = resto;
        }
    }
    for (char *f = args + largo(args); f > args && f[-1] == ' '; ) *--f = 0;
    for (int i = 0; i < nordenes; i++) if (igual(ordenes[i].nombre, l)) { ordenes[i].f(args); return; }
    kprint("No conozco la orden \""); kprint(l); kprint("\". Escribe ayuda.\n");
}

void shell_bucle(void) {
    char linea[MAX_LINEA];
    kprint("Escribe ayuda para ver las ordenes.\n");
    for (;;) {
        kprint("kira:"); kprint(actual); kprint("> ");
        int n = 0;
        for (;;) {
            int c = leer_tecla();
            if (c == '\n') { kputc('\n'); break; }
            if (c == '\b' || c == 127) { if (n) { n--; kputc('\b'); } continue; }
            if (c == '\t') c = ' ';
            if (c < 32 || c > 126 || n >= MAX_LINEA - 1) continue;
            linea[n++] = (char)c;
            kputc((char)c);
        }
        linea[n] = 0;
        ejecutar(linea);
    }
}
"""

_IDT2_H = r"""/* idt.h (v2) — interrupciones; ahora una interrupción puede volver a OTRA tarea (multitarea) */
#ifndef IDT_H
#define IDT_H
#include <stdint.h>

struct registros {
    uint32_t gs, fs, es, ds;
    uint32_t edi, esi, ebp, esp, ebx, edx, ecx, eax;   /* pusha */
    uint32_t num, err;                                 /* los mete el trocito de isr.s */
    uint32_t eip, cs, eflags;                          /* los mete el procesador */
    uint32_t useresp, ss;                              /* solo si venía del modo usuario */
};

typedef void (*manejador_t)(struct registros *r);

void idt_init(void);
void idt_poner_manejador(int n, manejador_t m);
void irq_fin(int irq);          /* débil aquí; pic.c pone la de verdad */
typedef struct registros *(*planificador_t)(struct registros *r);
void idt_poner_planificador(planificador_t p);   /* se le llama en cada tic del reloj (y si se pide cambiar) */
void idt_pedir_cambio(void);                      /* la tarea actual ya no puede seguir: cambia ahora */
void idt_poner_usuario(int n);                    /* la interrupción n se puede llamar desde el modo usuario */

#endif
"""

_IDT2_C = r"""/* idt.c (v2) — IDT con 32 excepciones + 16 IRQ + la 0x80 (llamadas al sistema); isr_manejador devuelve la pila
   por la que hay que volver: así el reloj puede cambiar de tarea */
#include "idt.h"
#include "consola.h"

struct idt_entrada {
    uint16_t base_baja;
    uint16_t selector;
    uint8_t  cero;
    uint8_t  tipo;
    uint16_t base_alta;
} __attribute__((packed));

struct idt_puntero {
    uint16_t limite;
    uint32_t base;
} __attribute__((packed));

static struct idt_entrada idt[256];
static struct idt_puntero idtp;
static manejador_t manejadores[256];
extern uint32_t isr_tabla[];                 /* isr.s: direcciones de isr0..isr47 */

static const char *NOMBRES[32] = {
    "division por cero", "depuracion", "NMI", "punto de ruptura", "desbordamiento", "fuera de rango",
    "instruccion invalida", "sin coprocesador", "doble fallo", "segmento del coprocesador", "TSS invalida",
    "segmento no presente", "fallo de pila", "proteccion general", "fallo de pagina", "reservada",
    "error de coma flotante", "alineacion", "comprobacion de maquina", "SIMD", "virtualizacion", "proteccion de control",
    "reservada", "reservada", "reservada", "reservada", "reservada", "reservada", "hipervisor", "VMM", "seguridad",
    "reservada"
};

void __attribute__((weak)) irq_fin(int irq) { (void)irq; }

void idt_poner_manejador(int n, manejador_t m) {
    if (n >= 0 && n < 256) manejadores[n] = m;
}

static void idt_poner(int n, uint32_t base, uint16_t sel, uint8_t tipo);
void idt_poner_usuario(int n) { if (n >= 0 && n < 256) idt[n].tipo = 0xEE; }   /* DPL 3 */

static void idt_poner(int n, uint32_t base, uint16_t sel, uint8_t tipo) {
    idt[n].base_baja = base & 0xFFFF;
    idt[n].base_alta = (base >> 16) & 0xFFFF;
    idt[n].selector  = sel;
    idt[n].cero      = 0;
    idt[n].tipo      = tipo;
}

static planificador_t planificador = 0;
static volatile int cambio_pedido = 0;
void idt_poner_planificador(planificador_t p) { planificador = p; }
void idt_pedir_cambio(void) { cambio_pedido = 1; }

struct registros *isr_manejador(struct registros *r) {
    if (manejadores[r->num]) {
        manejadores[r->num](r);
    } else if (r->num < 32) {
        kprint("Excepcion ");
        kprint_dec(r->num);
        kprint(" (");
        kprint(NOMBRES[r->num]);
        kprint(") en eip=");
        kprint_hex(r->eip);
        kprint("\n");
        if (r->num != 3) {                         /* el punto de ruptura (int 3) se puede seguir */
            kprint("PANICO: sistema detenido\n");
            for (;;) __asm__ volatile ("cli; hlt");
        }
    }
    if (r->num >= 32 && r->num < 48) irq_fin((int)r->num - 32);
    if (planificador && (r->num == 32 || cambio_pedido)) {
        cambio_pedido = 0;
        r = planificador(r);
    }
    return r;
}

void idt_init(void) {
    idtp.limite = sizeof(idt) - 1;
    idtp.base   = (uint32_t)&idt;
    for (int i = 0; i < 48; i++) idt_poner(i, isr_tabla[i], 0x08, 0x8E);
    idt_poner(128, isr_tabla[48], 0x08, 0x8E);         /* llamadas al sistema (se abre al usuario en la etapa 13) */
    __asm__ volatile ("lidt %0" : : "m"(idtp));
    kprint("IDT OK\n");
}
"""

_ISR2_S = r"""; isr.s (v2) — interrupciones 0..47 y la 0x80; vuelve por la pila que diga isr_manejador (cambio de tarea)
extern isr_manejador

%macro ISR_SIN_ERROR 1
global isr%1
isr%1:
    push dword 0            ; código de error falso (para que la pila sea igual en todas)
    push dword %1
    jmp isr_comun
%endmacro

%macro ISR_CON_ERROR 1
global isr%1
isr%1:
    push dword %1           ; el procesador ya metió el código de error
    jmp isr_comun
%endmacro

ISR_SIN_ERROR 0
ISR_SIN_ERROR 1
ISR_SIN_ERROR 2
ISR_SIN_ERROR 3
ISR_SIN_ERROR 4
ISR_SIN_ERROR 5
ISR_SIN_ERROR 6
ISR_SIN_ERROR 7
ISR_CON_ERROR 8
ISR_SIN_ERROR 9
ISR_CON_ERROR 10
ISR_CON_ERROR 11
ISR_CON_ERROR 12
ISR_CON_ERROR 13
ISR_CON_ERROR 14
ISR_SIN_ERROR 15
ISR_SIN_ERROR 16
ISR_CON_ERROR 17
ISR_SIN_ERROR 18
ISR_SIN_ERROR 19
ISR_SIN_ERROR 20
ISR_CON_ERROR 21
ISR_SIN_ERROR 22
ISR_SIN_ERROR 23
ISR_SIN_ERROR 24
ISR_SIN_ERROR 25
ISR_SIN_ERROR 26
ISR_SIN_ERROR 27
ISR_SIN_ERROR 28
ISR_CON_ERROR 29
ISR_CON_ERROR 30
ISR_SIN_ERROR 31
%assign i 32
%rep 16
ISR_SIN_ERROR i
%assign i i+1
%endrep
ISR_SIN_ERROR 128

isr_comun:
    pusha
    push ds
    push es
    push fs
    push gs
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    push esp                ; argumento: puntero a struct registros
    call isr_manejador
    mov esp, eax            ; la pila de la tarea que toca ahora (la misma si no hay cambio)
    pop gs
    pop fs
    pop es
    pop ds
    popa
    add esp, 8              ; quita número y código de error
    iret

section .data
global isr_tabla
isr_tabla:
%assign i 0
%rep 48
    dd isr %+ i
%assign i i+1
%endrep
    dd isr128
"""

_TAREAS_H = r"""/* tareas.h — multitarea: varias tareas que se turnan con cada tic del reloj */
#ifndef TAREAS_H
#define TAREAS_H
#include <stdint.h>
#include "idt.h"
void tareas_init(void);                                      /* la tarea 0 es kernel_main */
int tarea_crear(void (*f)(void), const char *nombre);         /* tarea del kernel; devuelve su número o -1 */
int tarea_crear_usuario(void (*f)(void), uint32_t pila_usuario, const char *nombre);   /* modo usuario (etapa 13) */
void tarea_salir(void);                                      /* la tarea actual termina */
void tarea_matar(int n);                                     /* parar otra tarea */
void tarea_matar_actual(void);                               /* desde una interrupción: matar la que corre */
int tarea_viva(int n);
int tarea_actual(void);
void tareas_listar(void);
uint32_t tarea_tics(int n);                                  /* cuántos turnos ha tenido */
#endif
"""

_TAREAS_C = r"""/* tareas.c — planificador por turnos (round robin) con cambio de contexto en la interrupción del reloj.
   Cada tarea tiene su pila; al cambiar, se guarda dónde estaba la pila de la que sale (con todos sus registros) y se
   vuelve por la pila de la que entra. */
#include <stdint.h>
#include "tareas.h"
#include "consola.h"
#include "memoria.h"

#define MAX_TAREAS 8
#define PILA 8192
enum { LIBRE = 0, LISTA = 1, MUERTA = 2 };
struct tarea {
    struct registros *regs;
    uint8_t *pila;
    int estado, usuario;
    uint32_t turnos;
    char nombre[16];
};
static struct tarea t[MAX_TAREAS];
static int actual = 0, encendido = 0;

void __attribute__((weak)) tss_poner_pila(uint32_t esp0) { (void)esp0; }   /* gdt.c de la etapa 13 pone la real */

static struct registros *planificar(struct registros *r) {
    t[actual].regs = r;
    t[actual].turnos++;
    int sig = actual;
    for (int i = 1; i <= MAX_TAREAS; i++) {
        int k = (actual + i) % MAX_TAREAS;
        if (t[k].estado == LISTA) { sig = k; break; }
    }
    if (t[sig].estado != LISTA) sig = 0;                     /* la tarea 0 (el kernel) nunca muere */
    actual = sig;
    if (t[actual].pila) tss_poner_pila((uint32_t)t[actual].pila + PILA);
    return t[actual].regs;
}

void tareas_init(void) {
    t[0].estado = LISTA; t[0].usuario = 0;
    const char *n = "kernel";
    for (int i = 0; n[i]; i++) t[0].nombre[i] = n[i];
    idt_poner_planificador(planificar);
    encendido = 1;
}

static void poner_nombre(int k, const char *n) {
    int i = 0;
    for (; n[i] && i < 15; i++) t[k].nombre[i] = n[i];
    t[k].nombre[i] = 0;
}

static void tarea_fin_natural(void) { tarea_salir(); }

static int hueco(void) {
    for (int k = 1; k < MAX_TAREAS; k++) if (t[k].estado != LISTA && k != actual) return k;
    return -1;
}

static int preparar(int k, void (*f)(void), int usuario, uint32_t pila_usuario, const char *nombre) {
    if (!t[k].pila) t[k].pila = kmalloc(PILA);
    if (!t[k].pila) return -1;
    uint32_t *cima = (uint32_t *)(t[k].pila + PILA);
    /* lo que el procesador saca con iret (y, para el modo usuario, también su pila) */
    if (usuario) {
        *--cima = 0x23;                                   /* ss del usuario */
        *--cima = pila_usuario;                           /* esp del usuario */
    } else {
        *--cima = (uint32_t)tarea_fin_natural;             /* si la función termina, «vuelve» aquí */
    }
    uint32_t marco_cima = (uint32_t)cima;
    (void)marco_cima;
    *--cima = 0x202;                                      /* eflags: interrupciones encendidas */
    *--cima = usuario ? 0x1B : 0x08;                      /* cs */
    *--cima = (uint32_t)f;                                /* eip */
    *--cima = 0;                                          /* err */
    *--cima = 32;                                         /* num (como si viniera del reloj) */
    for (int i = 0; i < 8; i++) *--cima = 0;              /* eax..edi (pusha) */
    uint32_t seg = usuario ? 0x23 : 0x10;
    for (int i = 0; i < 4; i++) *--cima = seg;            /* ds, es, fs, gs */
    t[k].regs = (struct registros *)cima;
    t[k].usuario = usuario;
    t[k].turnos = 0;
    poner_nombre(k, nombre);
    t[k].estado = LISTA;                                  /* lo último: así el reloj no la coge a medias */
    return k;
}

int tarea_crear(void (*f)(void), const char *nombre) {
    if (!encendido) return -1;
    __asm__ volatile ("cli");
    int k = hueco(), r = k < 0 ? -1 : preparar(k, f, 0, 0, nombre);
    __asm__ volatile ("sti");
    return r;
}

int tarea_crear_usuario(void (*f)(void), uint32_t pila_usuario, const char *nombre) {
    if (!encendido) return -1;
    __asm__ volatile ("cli");
    int k = hueco(), r = k < 0 ? -1 : preparar(k, f, 1, pila_usuario, nombre);
    __asm__ volatile ("sti");
    return r;
}

void tarea_matar_actual(void) {
    if (actual == 0) return;                              /* al kernel no se le mata */
    t[actual].estado = MUERTA;
    idt_pedir_cambio();
}

void tarea_salir(void) {
    __asm__ volatile ("cli");
    tarea_matar_actual();
    __asm__ volatile ("sti");
    for (;;) __asm__ volatile ("hlt");                    /* el próximo tic ya no la elige */
}

int tarea_viva(int n) { return n >= 0 && n < MAX_TAREAS && t[n].estado == LISTA; }
int tarea_actual(void) { return actual; }
uint32_t tarea_tics(int n) { return (n >= 0 && n < MAX_TAREAS) ? t[n].turnos : 0; }

void tareas_listar(void) {
    for (int k = 0; k < MAX_TAREAS; k++) {
        if (t[k].estado == LIBRE) continue;
        kprint("  "); kprint_dec((uint32_t)k); kprint(". "); kprint(t[k].nombre);
        kprint(t[k].estado == LISTA ? " (en marcha" : " (terminada");
        kprint(t[k].usuario ? ", modo usuario" : "");
        kprint(", "); kprint_dec(t[k].turnos); kprint(" turnos)");
        if (k == actual) kprint(" <- ahora");
        kputc('\n');
    }
}

void tarea_matar(int n) {                                 /* desde fuera (la tarea 0): por ejemplo, si no acaba */
    if (n <= 0 || n >= MAX_TAREAS || n == actual) return;
    __asm__ volatile ("cli");
    if (t[n].estado == LISTA) t[n].estado = MUERTA;
    __asm__ volatile ("sti");
}
"""

_GDT2_C = r"""/* gdt.c (v2, etapa 13+) — GDT con segmentos del kernel (anillo 0), del USUARIO (anillo 3) y la TSS: la pila del
   kernel a la que salta el procesador cuando un programa de usuario hace una llamada al sistema o le interrumpen */
#include <stdint.h>
#include "consola.h"

struct gdt_entrada {
    uint16_t limite_bajo;
    uint16_t base_baja;
    uint8_t  base_media;
    uint8_t  acceso;
    uint8_t  granularidad;
    uint8_t  base_alta;
} __attribute__((packed));

struct gdt_puntero {
    uint16_t limite;
    uint32_t base;
} __attribute__((packed));

static struct gdt_entrada gdt[6];

struct tss {
    uint32_t prev, esp0, ss0, esp1, ss1, esp2, ss2, cr3, eip, eflags, eax, ecx, edx, ebx, esp, ebp, esi, edi;
    uint32_t es, cs, ss, ds, fs, gs, ldt;
    uint16_t trap, iomap;
} __attribute__((packed));
static struct tss tss;

void tss_poner_pila(uint32_t esp0) { tss.esp0 = esp0; }
static struct gdt_puntero gdtp;

extern void gdt_cargar(uint32_t puntero);     /* gdt_asm.s */

static void gdt_poner(int i, uint32_t base, uint32_t limite, uint8_t acceso, uint8_t gran) {
    gdt[i].base_baja    = base & 0xFFFF;
    gdt[i].base_media   = (base >> 16) & 0xFF;
    gdt[i].base_alta    = (base >> 24) & 0xFF;
    gdt[i].limite_bajo  = limite & 0xFFFF;
    gdt[i].granularidad = (uint8_t)(((limite >> 16) & 0x0F) | (gran & 0xF0));
    gdt[i].acceso       = acceso;
}

void gdt_init(void) {
    gdtp.limite = sizeof(gdt) - 1;
    gdtp.base   = (uint32_t)&gdt;
    gdt_poner(0, 0, 0, 0, 0);                    /* descriptor nulo (obligatorio) */
    gdt_poner(1, 0, 0xFFFFFFFF, 0x9A, 0xCF);     /* 0x08: código del kernel */
    gdt_poner(2, 0, 0xFFFFFFFF, 0x92, 0xCF);     /* 0x10: datos del kernel */
    gdt_poner(3, 0, 0xFFFFFFFF, 0xFA, 0xCF);     /* 0x18 (|3 = 0x1B): código del usuario */
    gdt_poner(4, 0, 0xFFFFFFFF, 0xF2, 0xCF);     /* 0x20 (|3 = 0x23): datos del usuario */
    uint8_t *b = (uint8_t *)&tss;
    for (uint32_t i = 0; i < sizeof(tss); i++) b[i] = 0;
    tss.ss0 = 0x10;
    tss.iomap = sizeof(tss);                     /* sin mapa de puertos: el usuario no puede tocar ninguno */
    gdt_poner(5, (uint32_t)&tss, sizeof(tss) - 1, 0x89, 0x00);   /* 0x28: la TSS */
    gdt_cargar((uint32_t)&gdtp);
    __asm__ volatile ("ltr %%ax" : : "a"(0x28));
    kprint("GDT OK (con modo usuario y TSS)\n");
}
"""

_USUARIO_H = r"""/* usuario.h — modo usuario (anillo 3) y llamadas al sistema (int 0x80) */
#ifndef USUARIO_H
#define USUARIO_H
#include <stdint.h>
/* llamadas: eax = número; ebx, ecx = datos; la respuesta vuelve en eax */
#define SYS_ESCRIBIR 1      /* ebx = texto, ecx = largo */
#define SYS_SALIR    2      /* ebx = código */
#define SYS_TIEMPO   3      /* devuelve los tics del reloj */
#define USUARIO_DESDE 0x00800000u          /* zona de los programas de usuario: 8 MB … 12 MB */
#define USUARIO_HASTA 0x00C00000u
void usuario_init(void);                    /* llamadas al sistema + vigilancia de fallos del usuario */
int usuario_ejecutar(void (*f)(void), uint32_t pila, const char *nombre);   /* crea la tarea en anillo 3 */
int usuario_ultimo_motivo(char *sal, int max);   /* por qué terminó el último programa */
#endif
"""

_USUARIO_C = r"""/* usuario.c — los programas de usuario corren en el ANILLO 3: no pueden usar instrucciones privilegiadas (cli, hlt,
   in/out…) ni tocar la memoria del kernel. Solo piden cosas al kernel con «int 0x80». Si hacen algo prohibido, el
   procesador salta al kernel (fallo de protección o de página) y el kernel cierra ese programa: el resto sigue. */
#include <stdint.h>
#include "usuario.h"
#include "idt.h"
#include "tareas.h"
#include "consola.h"
#include "timer.h"

static char motivo[96];

static void apuntar(const char *a, const char *b) {
    int n = 0;
    for (int i = 0; a[i] && n < 95; i++) motivo[n++] = a[i];
    for (int i = 0; b && b[i] && n < 95; i++) motivo[n++] = b[i];
    motivo[n] = 0;
}

int usuario_ultimo_motivo(char *sal, int max) {
    int i = 0;
    for (; motivo[i] && i < max - 1; i++) sal[i] = motivo[i];
    sal[i] = 0;
    return i;
}

/* la zona 8–12 MB se marca como «de usuario» en la paginación; el resto (el kernel) NO */
static void abrir_zona(void) {
    uint32_t cr3;
    __asm__ volatile ("mov %%cr3, %0" : "=r"(cr3));
    uint32_t *dir = (uint32_t *)(cr3 & 0xFFFFF000u);
    for (uint32_t d = USUARIO_DESDE; d < USUARIO_HASTA; d += 0x400000u) {
        uint32_t i = d >> 22;
        dir[i] |= 0x4;
        uint32_t *tabla = (uint32_t *)(dir[i] & 0xFFFFF000u);
        for (uint32_t k = 0; k < 1024; k++) tabla[k] |= 0x4;
    }
    __asm__ volatile ("mov %%cr3, %0; mov %0, %%cr3" : "=r"(cr3) : : "memory");
}

static int en_zona(uint32_t p, uint32_t n) {
    return p >= USUARIO_DESDE && n <= USUARIO_HASTA - USUARIO_DESDE && p + n <= USUARIO_HASTA;
}

static void llamada(struct registros *r) {
    switch (r->eax) {
    case SYS_ESCRIBIR: {
        uint32_t p = r->ebx, n = r->ecx;
        if (!en_zona(p, n) || n > 4096) { r->eax = (uint32_t)-1; return; }   /* no puede pedir leer el kernel */
        const char *s = (const char *)p;
        for (uint32_t i = 0; i < n; i++) kputc(s[i]);
        r->eax = n;
        return;
    }
    case SYS_SALIR:
        apuntar("termino bien", 0);
        tarea_matar_actual();
        return;
    case SYS_TIEMPO:
        r->eax = timer_tics();
        return;
    default:
        r->eax = (uint32_t)-1;
    }
}

static void fallo(struct registros *r) {
    if ((r->cs & 3) == 3) {                               /* venía de un programa de usuario: se le cierra */
        const char *que = r->num == 13 ? "intento algo prohibido (instruccion privilegiada o puerto)" :
                          r->num == 14 ? "intento tocar memoria que no es suya" :
                          r->num == 6 ? "ejecuto una instruccion invalida" : "fallo";
        kprint("[kernel] El programa de usuario "); kprint(que); kprint(": lo cierro. El sistema sigue.\n");
        apuntar("lo cerre: ", que);
        tarea_matar_actual();
        return;
    }
    kprint("Excepcion "); kprint_dec(r->num); kprint(" en el kernel, eip="); kprint_hex(r->eip);
    kprint("\nPANICO: sistema detenido\n");
    for (;;) __asm__ volatile ("cli; hlt");
}

void usuario_init(void) {
    abrir_zona();
    idt_poner_manejador(128, llamada);
    idt_poner_usuario(128);
    idt_poner_manejador(13, fallo);
    idt_poner_manejador(14, fallo);
    idt_poner_manejador(6, fallo);
    kprint("Modo usuario listo (llamadas al sistema por int 0x80)\n");
}

int usuario_ejecutar(void (*f)(void), uint32_t pila, const char *nombre) {
    motivo[0] = 0;
    return tarea_crear_usuario(f, pila, nombre);
}
"""

_USUARIO_DEMO_S = r"""; usuario_demo.s — dos programitas de usuario (código que funciona esté donde esté): el kernel los COPIA a la zona
; de usuario (8 MB) y los lanza en el anillo 3. «bueno» saluda y termina bien; «travieso» intenta apagar las
; interrupciones (cli), algo prohibido para un programa: el procesador avisa al kernel y el kernel lo cierra.
section .text
global usuario_demo_ini, usuario_demo_fin, usuario_demo_bueno, usuario_demo_travieso

usuario_demo_ini:
usuario_demo_bueno:
    call .aqui
.aqui:
    pop esi
    lea ebx, [esi + (msg_bueno - .aqui)]
    mov ecx, msg_bueno_fin - msg_bueno
    mov eax, 1                 ; SYS_ESCRIBIR
    int 0x80
    mov eax, 2                 ; SYS_SALIR
    xor ebx, ebx
    int 0x80
.para:
    jmp .para

usuario_demo_travieso:
    call .aqui2
.aqui2:
    pop esi
    lea ebx, [esi + (msg_trav - .aqui2)]
    mov ecx, msg_trav_fin - msg_trav
    mov eax, 1
    int 0x80
    cli                        ; PROHIBIDO en el anillo 3 → fallo de protección general
    mov eax, 2                 ; (aquí ya no llega)
    int 0x80
.para2:
    jmp .para2

msg_bueno: db "Hola desde el modo usuario (anillo 3): pido al kernel que escriba esto", 10
msg_bueno_fin:
msg_trav: db "Soy un programa travieso: voy a intentar apagar las interrupciones...", 10
msg_trav_fin:
usuario_demo_fin:
"""

_PROGRAMA_H = r"""/* programa.h — cargar programas (ELF de 32 bits) desde el disco y ejecutarlos en modo usuario */
#ifndef PROGRAMA_H
#define PROGRAMA_H
int programa_buscar(const char *nombre, char *ruta, int max);   /* 1 si lo encuentra */
int programa_ejecutar(const char *ruta);                        /* 0 = terminó bien */
void programa_listar(void);
#endif
"""

_PROGRAMA_C = r"""/* programa.c — lee un programa ELF de 32 bits del disco (ext4), comprueba que todo cae en la zona de usuario
   (8–12 MB), copia sus trozos a la memoria, pone a cero el resto y lo lanza en el ANILLO 3 como una tarea más.
   Lo busca en /programas y en /home/<usuario>/kira_portatil/kernel/programas (donde lo deja el taller de Kira). */
#include <stdint.h>
#include "programa.h"
#include "ext4.h"
#include "usuario.h"
#include "tareas.h"
#include "timer.h"
#include "consola.h"

#define MAX_ELF (128 * 1024)
static uint8_t imagen[MAX_ELF];

static uint16_t u16(const uint8_t *b) { return (uint16_t)(b[0] | (b[1] << 8)); }
static uint32_t u32(const uint8_t *b) { return b[0] | (b[1] << 8) | (b[2] << 16) | ((uint32_t)b[3] << 24); }
static int largo(const char *s) { int n = 0; while (s[n]) n++; return n; }

static void unir(char *sal, int max, const char *a, const char *b, const char *c, const char *d) {
    const char *partes[4] = {a, b, c, d};
    int n = 0;
    for (int k = 0; k < 4; k++) for (int i = 0; partes[k] && partes[k][i] && n < max - 1; i++) sal[n++] = partes[k][i];
    sal[n] = 0;
}

static int probar_en(const char *carpeta, const char *nombre, char *ruta, int max) {
    unir(ruta, max, carpeta, "/", nombre, 0);
    if (ext4_existe(ruta) == 1) return 1;
    unir(ruta, max, carpeta, "/", nombre, ".elf");
    return ext4_existe(ruta) == 1;
}

int programa_buscar(const char *nombre, char *ruta, int max) {
    if (nombre[0] == '/') { unir(ruta, max, nombre, 0, 0, 0); return ext4_existe(ruta) == 1; }
    if (probar_en("/programas", nombre, ruta, max)) return 1;
    static char gente[16][32];
    int n = ext4_nombres("/home", gente, 16);
    for (int i = 0; i < n; i++) {
        char carpeta[96];
        unir(carpeta, sizeof(carpeta), "/home/", gente[i], "/kira_portatil/kernel/programas", 0);
        if (probar_en(carpeta, nombre, ruta, max)) return 1;
    }
    return 0;
}

void programa_listar(void) {
    static char nombres[24][32];
    int total = 0;
    int n = ext4_nombres("/programas", nombres, 24);
    for (int i = 0; i < n; i++) { kprint("  /programas/"); kprint(nombres[i]); kputc('\n'); total++; }
    static char gente[16][32];
    int g = ext4_nombres("/home", gente, 16);
    for (int i = 0; i < g; i++) {
        char carpeta[96];
        unir(carpeta, sizeof(carpeta), "/home/", gente[i], "/kira_portatil/kernel/programas", 0);
        n = ext4_nombres(carpeta, nombres, 24);
        for (int k = 0; k < n; k++) {
            int l = largo(nombres[k]);
            if (l < 4 || nombres[k][l - 4] != '.' || nombres[k][l - 3] != 'e') continue;   /* solo los .elf */
            kprint("  "); kprint(carpeta); kputc('/'); kprint(nombres[k]); kputc('\n'); total++;
        }
    }
    if (!total) kprint("No hay programas en el disco (el taller de Kira los deja en kira_portatil/kernel/programas)\n");
}

static int en_zona(uint32_t p, uint32_t n) {
    return p >= USUARIO_DESDE && n <= USUARIO_HASTA - USUARIO_DESDE && p + n <= USUARIO_HASTA - 0x10000;   /* deja sitio a la pila */
}

int programa_ejecutar(const char *ruta) {
    uint32_t tam = 0;
    if (ext4_leer(ruta, imagen, MAX_ELF, &tam) != 0) { kprint("No puedo leer "); kprint(ruta); kputc('\n'); return -1; }
    if (tam > MAX_ELF) { kprint("Programa demasiado grande (maximo 128 KB)\n"); return -1; }
    if (tam < 52 || imagen[0] != 0x7F || imagen[1] != 'E' || imagen[2] != 'L' || imagen[3] != 'F') {
        kprint("No es un programa ELF\n"); return -1;
    }
    if (imagen[4] != 1 || u16(imagen + 18) != 3 || u16(imagen + 16) != 2) {
        kprint("No es un ELF de 32 bits para x86 ejecutable\n"); return -1;
    }
    uint32_t entrada = u32(imagen + 24), phoff = u32(imagen + 28);
    uint16_t phsize = u16(imagen + 42), phnum = u16(imagen + 44);
    if (phsize < 32 || phoff + (uint32_t)phsize * phnum > tam || !phnum) { kprint("Cabecera del programa rota\n"); return -1; }
    for (int pase = 0; pase < 2; pase++) {                /* 1.º comprobar todo; 2.º copiar */
        for (uint16_t i = 0; i < phnum; i++) {
            const uint8_t *ph = imagen + phoff + (uint32_t)i * phsize;
            if (u32(ph) != 1) continue;                   /* solo los trozos que se cargan (PT_LOAD) */
            uint32_t off = u32(ph + 4), va = u32(ph + 8), fsz = u32(ph + 16), msz = u32(ph + 20);
            if (pase == 0) {
                if (!en_zona(va, msz) || fsz > msz || off + fsz > tam) {
                    kprint("El programa quiere memoria fuera de su zona (8-12 MB): no lo cargo\n"); return -1;
                }
                continue;
            }
            uint8_t *dst = (uint8_t *)va;
            for (uint32_t k = 0; k < fsz; k++) dst[k] = imagen[off + k];
            for (uint32_t k = fsz; k < msz; k++) dst[k] = 0;
        }
    }
    if (!en_zona(entrada, 1)) { kprint("El punto de entrada no esta en su zona\n"); return -1; }
    kprint("Cargo "); kprint(ruta); kprint(" ("); kprint_dec(tam); kprint(" bytes) y lo ejecuto en modo usuario:\n");
    int k = usuario_ejecutar((void (*)(void))entrada, USUARIO_HASTA - 16, "programa");
    if (k < 0) { kprint("No hay sitio para otra tarea\n"); return -1; }
    uint32_t fin = timer_tics() + 1000;                   /* 10 segundos como mucho */
    while (tarea_viva(k) && timer_tics() < fin) __asm__ volatile ("hlt");
    if (tarea_viva(k)) { tarea_matar(k); kprint("[kernel] El programa no acababa: lo he parado\n"); return -1; }
    char m[96];
    usuario_ultimo_motivo(m, sizeof(m));
    kprint("[kernel] El programa "); kprint(m[0] ? m : "termino"); kputc('\n');
    return (m[0] == 't') ? 0 : -1;
}
"""

_RED2_H = r"""/* red.h (v2) — tarjeta de red Intel e1000 (la que pone QEMU) */
#ifndef RED_H
#define RED_H
#include <stdint.h>
int red_iniciar(void);                                /* 1 si hay tarjeta y está lista */
void red_enviar(const uint8_t *datos, uint16_t largo);  /* una trama Ethernet entera */
int red_recibir(uint8_t *destino, int max);           /* una trama recibida (su largo) o 0 */
void red_mac(uint8_t *mac);
void red_probar(void);                                /* la prueba de la etapa 8 (ARP) */
#endif
"""

_RED2_C = r"""/* red.c (v2, etapa 15+) — driver de la tarjeta Intel e1000 con piezas para la pila de red (iniciar, enviar,
   recibir); (82540EM): lee su MAC, monta las colas de envío y recepción y pregunta
   por ARP quién es el router virtual de QEMU (10.0.2.2). QEMU corre con la red AISLADA (restrict=on): no sale a
   internet ni ve tu casa. */
#include <stdint.h>
#include "red.h"
#include "pci.h"
#include "consola.h"
#include "memoria.h"
#include "timer.h"

#define CTRL   0x0000
#define EERD   0x0014
#define ICR    0x00C0
#define IMC    0x00D8
#define RCTL   0x0100
#define TCTL   0x0400
#define TIPG   0x0410
#define RDBAL  0x2800
#define RDBAH  0x2804
#define RDLEN  0x2808
#define RDH    0x2810
#define RDT    0x2818
#define TDBAL  0x3800
#define TDBAH  0x3804
#define TDLEN  0x3808
#define TDH    0x3810
#define TDT    0x3818
#define MTA    0x5200
#define RAL    0x5400
#define RAH    0x5404

#define NRX 32
#define NTX 8

struct rx_desc { uint64_t dir; uint16_t largo; uint16_t suma; uint8_t estado; uint8_t errores; uint16_t especial; } __attribute__((packed));
struct tx_desc { uint64_t dir; uint16_t largo; uint8_t cso; uint8_t orden; uint8_t estado; uint8_t css; uint16_t especial; } __attribute__((packed));

static volatile struct rx_desc rx[NRX] __attribute__((aligned(16)));
static volatile struct tx_desc tx[NTX] __attribute__((aligned(16)));
static uint8_t rx_buf[NRX][2048] __attribute__((aligned(16)));
static uint8_t tx_buf[NTX][2048] __attribute__((aligned(16)));
static uint32_t base = 0;
static uint8_t mac[6];
static int rx_cur = 0, tx_cur = 0;

static void escribe(uint32_t reg, uint32_t v) { *(volatile uint32_t *)(base + reg) = v; }
static uint32_t lee(uint32_t reg) { return *(volatile uint32_t *)(base + reg); }

static void hex2(uint8_t v) { const char *h = "0123456789abcdef"; kputc(h[v >> 4]); kputc(h[v & 0xF]); }
static void escribe_mac(const uint8_t *m) { for (int i = 0; i < 6; i++) { if (i) kputc(':'); hex2(m[i]); } }

static int eeprom(uint8_t dir, uint16_t *dato) {
    escribe(EERD, 1u | ((uint32_t)dir << 8));
    for (int i = 0; i < 100000; i++) {
        uint32_t v = lee(EERD);
        if (v & (1u << 4)) { *dato = (uint16_t)(v >> 16); return 1; }
    }
    return 0;
}

static void leer_mac(void) {
    uint16_t w;
    if (eeprom(0, &w)) {
        mac[0] = w & 0xFF; mac[1] = w >> 8;
        eeprom(1, &w); mac[2] = w & 0xFF; mac[3] = w >> 8;
        eeprom(2, &w); mac[4] = w & 0xFF; mac[5] = w >> 8;
    } else {
        uint32_t l = lee(RAL), h = lee(RAH);
        for (int i = 0; i < 4; i++) mac[i] = (uint8_t)(l >> (8 * i));
        mac[4] = (uint8_t)h; mac[5] = (uint8_t)(h >> 8);
    }
}

static void montar_colas(void) {
    for (int i = 0; i < NRX; i++) { rx[i].dir = (uint32_t)rx_buf[i]; rx[i].estado = 0; }
    escribe(RDBAL, (uint32_t)rx); escribe(RDBAH, 0);
    escribe(RDLEN, NRX * sizeof(struct rx_desc));
    escribe(RDH, 0); escribe(RDT, NRX - 1);
    /* EN | UPE | MPE | BAM | SECRC, búfer de 2048 */
    escribe(RCTL, (1u << 1) | (1u << 3) | (1u << 4) | (1u << 15) | (1u << 26));
    for (int i = 0; i < NTX; i++) { tx[i].dir = (uint32_t)tx_buf[i]; tx[i].orden = 0; tx[i].estado = 1; }
    escribe(TDBAL, (uint32_t)tx); escribe(TDBAH, 0);
    escribe(TDLEN, NTX * sizeof(struct tx_desc));
    escribe(TDH, 0); escribe(TDT, 0);
    escribe(TCTL, (1u << 1) | (1u << 3) | (0x10u << 4) | (0x40u << 12));   /* EN | PSP | CT | COLD */
    escribe(TIPG, 0x0060200A);
}

static int lista = 0;

void red_enviar(const uint8_t *datos, uint16_t largo) {
    uint8_t *b = tx_buf[tx_cur];
    for (int i = 0; i < largo; i++) b[i] = datos[i];
    for (int i = largo; i < 60; i++) b[i] = 0;               /* una trama Ethernet mide al menos 60 bytes */
    if (largo < 60) largo = 60;
    tx[tx_cur].largo = largo;
    tx[tx_cur].orden = 0x01 | 0x02 | 0x08;                   /* EOP | IFCS | RS */
    tx[tx_cur].estado = 0;
    tx_cur = (tx_cur + 1) % NTX;
    escribe(TDT, tx_cur);
}

int red_recibir(uint8_t *destino, int max) {          /* una trama recibida (su largo) o 0 si no hay */
    if (!lista || !(rx[rx_cur].estado & 1)) return 0;
    int n = rx[rx_cur].largo;
    if (n > max) n = max;
    for (int i = 0; i < n; i++) destino[i] = rx_buf[rx_cur][i];
    rx[rx_cur].estado = 0;
    escribe(RDT, rx_cur);
    rx_cur = (rx_cur + 1) % NRX;
    return n;
}

void red_mac(uint8_t *m) { for (int i = 0; i < 6; i++) m[i] = mac[i]; }

int red_iniciar(void) {
    if (lista) return 1;
    struct pci_disp d;
    if (!pci_buscar(0x8086, 0x100E, &d)) {
        kprint("Red: no hay tarjeta Intel e1000 (en tu portatil seguramente es otra marca: haria falta su driver)\n");
        return 0;
    }
    uint32_t orden = pci_leer(d.bus, d.disp, d.func, 0x04);
    pci_escribir(d.bus, d.disp, d.func, 0x04, orden | 0x06);   /* memoria + bus master (la tarjeta escribe en la RAM) */
    base = d.bar0 & 0xFFFFFFF0u;
    paginacion_mapear(base, 0x20000);
    escribe(CTRL, lee(CTRL) | (1u << 26));                      /* reinicio de la tarjeta */
    for (volatile int i = 0; i < 200000; i++) { }
    escribe(IMC, 0xFFFFFFFFu);                                  /* sin interrupciones: miramos nosotros */
    (void)lee(ICR);
    escribe(CTRL, lee(CTRL) | (1u << 6) | (1u << 5));           /* enlace arriba (SLU | ASDE) */
    for (int i = 0; i < 128; i++) escribe(MTA + 4 * i, 0);
    leer_mac();
    escribe(RAL, mac[0] | (mac[1] << 8) | (mac[2] << 16) | ((uint32_t)mac[3] << 24));
    escribe(RAH, mac[4] | (mac[5] << 8) | (1u << 31));
    kprint("Red: tarjeta e1000, MAC ");
    escribe_mac(mac);
    kputc('\n');
    montar_colas();
    lista = 1;
    return 1;
}

void red_probar(void) {
    if (!red_iniciar()) return;

    /* ARP: «¿quién tiene 10.0.2.2? díselo a 10.0.2.15» */
    uint8_t p[42];
    for (int i = 0; i < 6; i++) { p[i] = 0xFF; p[6 + i] = mac[i]; }
    p[12] = 0x08; p[13] = 0x06;                                 /* tipo ARP */
    p[14] = 0; p[15] = 1; p[16] = 0x08; p[17] = 0; p[18] = 6; p[19] = 4; p[20] = 0; p[21] = 1;   /* petición */
    for (int i = 0; i < 6; i++) { p[22 + i] = mac[i]; p[32 + i] = 0; }
    p[28] = 10; p[29] = 0; p[30] = 2; p[31] = 15;               /* yo: 10.0.2.15 */
    p[38] = 10; p[39] = 0; p[40] = 2; p[41] = 2;                /* busco: 10.0.2.2 */
    red_enviar(p, sizeof(p));

    uint32_t fin = timer_tics() + 300;                          /* 3 segundos como mucho */
    while (timer_tics() < fin) {
        if (rx[rx_cur].estado & 1) {
            uint8_t *r = rx_buf[rx_cur];
            int es_arp = r[12] == 0x08 && r[13] == 0x06 && r[21] == 2 &&
                         r[28] == 10 && r[29] == 0 && r[30] == 2 && r[31] == 2;
            rx[rx_cur].estado = 0;
            escribe(RDT, rx_cur);
            rx_cur = (rx_cur + 1) % NRX;
            if (es_arp) {
                kprint("RED OK: el router virtual 10.0.2.2 me ha contestado (MAC ");
                escribe_mac(r + 22);
                kprint(")\n");
                return;
            }
        } else {
            __asm__ volatile ("hlt");
        }
    }
    kprint("RED FALLA: nadie contesto al ARP\n");
}
"""

_IP_H = r"""/* ip.h — una pila de red pequeña: IP, UDP, ARP, DHCP y ping */
#ifndef IP_H
#define IP_H
int ip_dhcp(void);       /* pide una dirección al router; 1 = conseguida */
int ip_ping(void);       /* ping al router; 1 = contesta */
void ip_info(void);
#endif
"""

_IP_C = r"""/* ip.c — pila de red mínima sobre la e1000: tramas Ethernet, ARP (preguntar y contestar), IPv4 con su suma de
   comprobación, UDP y DHCP (descubrir → oferta → petición → aceptado) para que el router le dé una dirección; y un
   ping (ICMP) al router. En QEMU la red está AISLADA: solo existe su router virtual, nada de internet ni de tu casa. */
#include <stdint.h>
#include "ip.h"
#include "red.h"
#include "timer.h"
#include "consola.h"

static uint8_t mi_mac[6], router_mac[6];
static uint8_t mi_ip[4], router_ip[4], dns_ip[4], mascara[4];
static int con_ip = 0, router_conocido = 0;
static uint8_t trama[1600], rx[1600];
static const uint32_t XID = 0x4B495241;                   /* «KIRA» */

static void pon16(uint8_t *b, uint16_t v) { b[0] = (uint8_t)(v >> 8); b[1] = (uint8_t)v; }
static uint16_t lee16(const uint8_t *b) { return (uint16_t)((b[0] << 8) | b[1]); }
static void copia(uint8_t *d, const uint8_t *o, int n) { for (int i = 0; i < n; i++) d[i] = o[i]; }
static void ceros(uint8_t *d, int n) { for (int i = 0; i < n; i++) d[i] = 0; }
static int iguales(const uint8_t *a, const uint8_t *b, int n) { for (int i = 0; i < n; i++) if (a[i] != b[i]) return 0; return 1; }

static uint16_t suma(const uint8_t *b, int n) {           /* suma de comprobación de Internet (complemento a uno) */
    uint32_t s = 0;
    for (int i = 0; i + 1 < n; i += 2) s += (uint32_t)((b[i] << 8) | b[i + 1]);
    if (n & 1) s += (uint32_t)(b[n - 1] << 8);
    while (s >> 16) s = (s & 0xFFFF) + (s >> 16);
    return (uint16_t)~s;
}

static void escribe_ip(const uint8_t *ip) {
    for (int i = 0; i < 4; i++) { if (i) kputc('.'); kprint_dec(ip[i]); }
}

static int ethernet(const uint8_t *destino, uint16_t tipo) {
    copia(trama, destino, 6); copia(trama + 6, mi_mac, 6); pon16(trama + 12, tipo);
    return 14;
}

static int cabecera_ip(int pos, uint8_t proto, const uint8_t *origen, const uint8_t *destino, int datos) {
    uint8_t *h = trama + pos;
    ceros(h, 20);
    h[0] = 0x45; pon16(h + 2, (uint16_t)(20 + datos)); pon16(h + 4, 0x1234); h[8] = 64; h[9] = proto;
    copia(h + 12, origen, 4); copia(h + 16, destino, 4);
    pon16(h + 10, suma(h, 20));
    return pos + 20;
}

static void contestar_arp(const uint8_t *r) {             /* «¿quién tiene mi IP?» → «yo, con esta MAC» */
    static const uint8_t todos[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    (void)todos;
    int p = ethernet(r + 6, 0x0806);
    uint8_t *a = trama + p;
    pon16(a, 1); pon16(a + 2, 0x0800); a[4] = 6; a[5] = 4; pon16(a + 6, 2);
    copia(a + 8, mi_mac, 6); copia(a + 14, mi_ip, 4); copia(a + 18, r + 22, 6); copia(a + 24, r + 28, 4);
    red_enviar(trama, (uint16_t)(p + 28));
}

/* mira una trama recibida: contesta ARP si preguntan por mí; devuelve 1 si es la que se buscaba */
static int atender(int n) {
    if (n < 14) return 0;
    uint16_t tipo = lee16(rx + 12);
    if (tipo == 0x0806 && n >= 42 && con_ip && lee16(rx + 20) == 1 && iguales(rx + 38, mi_ip, 4)) contestar_arp(rx);
    return 1;
}

static void dhcp_enviar(uint8_t tipo, const uint8_t *pedida, const uint8_t *servidor) {
    static const uint8_t todos[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    static const uint8_t cero[4] = {0, 0, 0, 0}, bcast[4] = {255, 255, 255, 255};
    int p = ethernet(todos, 0x0800);
    int ip = p, udp = p + 20, b = udp + 8;
    uint8_t *m = trama + b;
    ceros(m, 300);
    m[0] = 1; m[1] = 1; m[2] = 6;                          /* petición, Ethernet, MAC de 6 */
    m[4] = (uint8_t)(XID >> 24); m[5] = (uint8_t)(XID >> 16); m[6] = (uint8_t)(XID >> 8); m[7] = (uint8_t)XID;
    m[10] = 0x80;                                          /* que la respuesta venga a todos (aún no tengo IP) */
    copia(m + 28, mi_mac, 6);
    m[236] = 99; m[237] = 130; m[238] = 83; m[239] = 99;   /* la «galleta mágica» de DHCP */
    int o = 240;
    m[o++] = 53; m[o++] = 1; m[o++] = tipo;
    if (pedida) { m[o++] = 50; m[o++] = 4; copia(m + o, pedida, 4); o += 4; }
    if (servidor) { m[o++] = 54; m[o++] = 4; copia(m + o, servidor, 4); o += 4; }
    m[o++] = 55; m[o++] = 3; m[o++] = 1; m[o++] = 3; m[o++] = 6;   /* quiero: máscara, router, DNS */
    m[o++] = 255;
    int largo = o < 300 ? 300 : o;
    uint8_t *u = trama + udp;
    pon16(u, 68); pon16(u + 2, 67); pon16(u + 4, (uint16_t)(8 + largo)); pon16(u + 6, 0);   /* UDP sin suma (vale en IPv4) */
    cabecera_ip(ip, 17, cero, bcast, 8 + largo);
    red_enviar(trama, (uint16_t)(b + largo));
}

/* espera una respuesta DHCP del tipo pedido; rellena la IP ofrecida y el servidor */
static int dhcp_esperar(uint8_t quiero, uint8_t *ofrecida, uint8_t *servidor) {
    uint32_t fin = timer_tics() + 300;
    while (timer_tics() < fin) {
        int n = red_recibir(rx, sizeof(rx));
        if (!n) { __asm__ volatile ("hlt"); continue; }
        atender(n);
        if (n < 14 + 20 + 8 + 240 || lee16(rx + 12) != 0x0800 || rx[23] != 17) continue;
        int ihl = (rx[14] & 0xF) * 4;
        const uint8_t *u = rx + 14 + ihl, *m = u + 8;
        if (lee16(u + 2) != 68 || m[0] != 2) continue;
        uint32_t xid = ((uint32_t)m[4] << 24) | ((uint32_t)m[5] << 16) | ((uint32_t)m[6] << 8) | m[7];
        if (xid != XID || m[236] != 99 || m[239] != 99) continue;
        int tipo = 0;
        const uint8_t *fin_m = rx + n;
        for (const uint8_t *o = m + 240; o < fin_m && *o != 255; ) {
            if (*o == 0) { o++; continue; }
            if (o + 1 >= fin_m || o + 2 + o[1] > fin_m) break;
            uint8_t cod = o[0], l = o[1];
            const uint8_t *v = o + 2;
            if (cod == 53 && l >= 1) tipo = v[0];
            if (cod == 54 && l >= 4) copia(servidor, v, 4);
            if (cod == 3 && l >= 4) copia(router_ip, v, 4);
            if (cod == 6 && l >= 4) copia(dns_ip, v, 4);
            if (cod == 1 && l >= 4) copia(mascara, v, 4);
            o += 2 + l;
        }
        if (tipo == 6) return -1;                          /* NAK: el router dice que no */
        if (tipo == quiero) { copia(ofrecida, m + 16, 4); return 1; }
    }
    return 0;
}

int ip_dhcp(void) {
    if (!red_iniciar()) return 0;
    red_mac(mi_mac);
    uint8_t oferta[4], servidor[4] = {0, 0, 0, 0}, ok[4];
    kprint("DHCP: pido una direccion al router...\n");
    for (int intento = 0; intento < 3; intento++) {
        dhcp_enviar(1, 0, 0);                              /* DISCOVER */
        if (dhcp_esperar(2, oferta, servidor) != 1) continue;   /* OFFER */
        kprint("DHCP: me ofrece "); escribe_ip(oferta); kputc('\n');
        dhcp_enviar(3, oferta, servidor);                  /* REQUEST */
        if (dhcp_esperar(5, ok, servidor) == 1) {          /* ACK */
            copia(mi_ip, ok, 4);
            con_ip = 1;
            static const uint8_t nada[4] = {0, 0, 0, 0};
            if (iguales(router_ip, nada, 4)) copia(router_ip, servidor, 4);   /* sin router anunciado (QEMU aislado): el servidor */
            if (iguales(dns_ip, nada, 4)) copia(dns_ip, servidor, 4);
            kprint("DHCP OK: mi IP es "); escribe_ip(mi_ip);
            kprint(", router "); escribe_ip(router_ip); kputc('\n');
            return 1;
        }
    }
    kprint("DHCP: nadie me ha dado una direccion\n");
    return 0;
}

static int arp_router(void) {
    static const uint8_t todos[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    for (int intento = 0; intento < 3 && !router_conocido; intento++) {
        int p = ethernet(todos, 0x0806);
        uint8_t *a = trama + p;
        pon16(a, 1); pon16(a + 2, 0x0800); a[4] = 6; a[5] = 4; pon16(a + 6, 1);
        copia(a + 8, mi_mac, 6); copia(a + 14, mi_ip, 4); ceros(a + 18, 6); copia(a + 24, router_ip, 4);
        red_enviar(trama, (uint16_t)(p + 28));
        uint32_t fin = timer_tics() + 100;
        while (timer_tics() < fin) {
            int n = red_recibir(rx, sizeof(rx));
            if (!n) { __asm__ volatile ("hlt"); continue; }
            atender(n);
            if (n >= 42 && lee16(rx + 12) == 0x0806 && lee16(rx + 20) == 2 && iguales(rx + 28, router_ip, 4)) {
                copia(router_mac, rx + 22, 6);
                router_conocido = 1;
                break;
            }
        }
    }
    return router_conocido;
}

int ip_ping(void) {
    if (!con_ip && !ip_dhcp()) return 0;
    if (!arp_router()) { kprint("PING: el router no contesta al ARP\n"); return 0; }
    for (uint16_t seq = 1; seq <= 3; seq++) {
        int p = ethernet(router_mac, 0x0800);
        int icmp = p + 20;
        uint8_t *c = trama + icmp;
        ceros(c, 40);
        c[0] = 8; pon16(c + 4, 0x4B49); pon16(c + 6, seq);  /* eco, identificador «KI», número */
        for (int i = 0; i < 32; i++) c[8 + i] = (uint8_t)('a' + i % 26);
        pon16(c + 2, suma(c, 40));
        cabecera_ip(p, 1, mi_ip, router_ip, 40);
        uint32_t salida = timer_tics();
        red_enviar(trama, (uint16_t)(icmp + 40));
        uint32_t fin = salida + 100;
        while (timer_tics() < fin) {
            int n = red_recibir(rx, sizeof(rx));
            if (!n) { __asm__ volatile ("hlt"); continue; }
            atender(n);
            if (n < 14 + 20 + 8 || lee16(rx + 12) != 0x0800 || rx[23] != 1) continue;
            int ihl = (rx[14] & 0xF) * 4;
            const uint8_t *r = rx + 14 + ihl;
            if (r[0] == 0 && lee16(r + 4) == 0x4B49 && lee16(r + 6) == seq) {
                kprint("PING OK: el router "); escribe_ip(router_ip); kprint(" contesta en ");
                kprint_dec((timer_tics() - salida) * 10); kprint(" ms\n");
                return 1;
            }
        }
    }
    kprint("PING: el router no contesta al ping (la red de QEMU puede no contestar pings)\n");
    return 0;
}

void ip_info(void) {
    if (!con_ip) { kprint("Sin direccion IP todavia (escribe: red)\n"); return; }
    kprint("IP "); escribe_ip(mi_ip); kprint("  mascara "); escribe_ip(mascara);
    kprint("  router "); escribe_ip(router_ip); kprint("  DNS "); escribe_ip(dns_ip); kputc('\n');
}
"""

# programas de USUARIO (no van dentro del kernel): el taller los compila aparte y los deja en programas/ (y en el disco)
PROGRAMAS = {"hola.c": r"""/* hola.c — un programa de usuario de Kira: NO es parte del kernel. Se compila aparte, se guarda en el disco y el
   kernel lo carga y lo ejecuta en el anillo 3. Solo puede pedirle cosas al kernel con «int 0x80». */
static int sys(int n, int a, int b) {
    int r;
    __asm__ volatile ("int $0x80" : "=a"(r) : "a"(n), "b"(a), "c"(b) : "memory");
    return r;
}
static int largo(const char *s) { int n = 0; while (s[n]) n++; return n; }
static void escribe(const char *s) { sys(1, (int)s, largo(s)); }
static void numero(unsigned n) {
    char b[12]; int i = 11; b[i] = 0;
    do { b[--i] = (char)('0' + n % 10); n /= 10; } while (n);
    escribe(b + i);
}

void _start(void) {
    escribe("Hola desde un programa cargado del disco! Soy hola.elf, corro en modo usuario.\n");
    unsigned t = (unsigned)sys(3, 0, 0);
    escribe("El kernel me dice que lleva ");
    numero(t / 100);
    escribe(" segundos encendido. Me despido.\n");
    sys(2, 0, 0);
    for (;;) { }
}
"""}
PROGRAMA_LD = r"""ENTRY(_start)
SECTIONS
{
    . = 0x00800000;
    .text   : { *(.text*) }
    .rodata : { *(.rodata*) }
    .data   : { *(.data*) }
    .bss    : { *(.bss*) *(COMMON) }
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
"""


def _k_desde5(titulo, decl, cuerpo):
    """kernel.c de las etapas 6+: el de la etapa 5 con más pasos antes de KERNEL_LISTO."""
    k = _K5.replace("/* kernel.c — etapa 5: memoria física, paginación y heap */", "/* kernel.c — " + titulo + " */")
    k = k.replace('#include "memoria.h"\n', '#include "memoria.h"\n' + decl)
    return k.replace('    kprint("KERNEL_LISTO\\n");', cuerpo + '    kprint("KERNEL_LISTO\\n");', 1)


_K6 = _k_desde5("etapa 6: el bus PCI (qué aparatos tiene el ordenador)", '#include "pci.h"\n',
                "    pci_listar();\n")
_K7 = _k_desde5("etapa 7: driver de disco ATA (leer y escribir sectores)", '#include "pci.h"\n#include "disco.h"\n',
                "    pci_listar();\n    disco_probar();\n")
_K8 = _k_desde5("etapa 8: driver de red e1000 (enviar y recibir tramas)",
                '#include "pci.h"\n#include "disco.h"\n#include "red.h"\n',
                "    pci_listar();\n    disco_probar();\n    red_probar();\n")
_K9 = _k_desde5("etapa 9: driver AHCI de solo lectura (el disco SATA de verdad)",
                '#include "pci.h"\n#include "disco.h"\n#include "red.h"\n#include "ahci.h"\n',
                "    pci_listar();\n    disco_probar();\n    red_probar();\n    ahci_probar();\n")

_K10 = _k_desde5("etapa 10: sistema de archivos ext4 de solo lectura",
                 '#include "pci.h"\n#include "disco.h"\n#include "red.h"\n#include "ahci.h"\n#include "ext4.h"\n',
                 "    pci_listar();\n    disco_probar();\n    red_probar();\n    ahci_probar();\n    ext4_probar();\n")

_COLA = '    kprint("KERNEL_LISTO\\n");\n    kprint("Escribe algo (Esc = reiniciar): ");\n    for (;;) __asm__ volatile ("hlt");'


def _k_shell(titulo, decl, cuerpo, ordenes):
    """kernel.c de las etapas 11+: arranca, hace sus pruebas y se queda en la consola «kira>»."""
    k = _k_desde5(titulo, decl, cuerpo)
    assert _COLA in k
    return k.replace(_COLA, '    kprint("KERNEL_LISTO\\n");\n    shell_init("' + titulo + '");\n' + ordenes +
                     '    shell_bucle();', 1)


_D11 = '#include "pci.h"\n#include "ahci.h"\n#include "ext4.h"\n#include "shell.h"\n'
_C11 = "    ahci_probar();\n    ext4_montar();\n"
_D12 = _D11 + r"""#include "tareas.h"

static volatile uint32_t cuenta_a = 0, cuenta_b = 0;
static volatile int parar_demo = 0;
static void contador_a(void) { while (!parar_demo) cuenta_a++; }
static void contador_b(void) { while (!parar_demo) cuenta_b++; }
static void o_tareas(const char *a) { (void)a; tareas_listar(); }
static void demo_multitarea(void) {
    tareas_init();
    int a = tarea_crear(contador_a, "contador A"), b = tarea_crear(contador_b, "contador B");
    uint32_t fin = timer_tics() + 50;
    while (timer_tics() < fin) __asm__ volatile ("hlt");
    if (a > 0 && b > 0 && cuenta_a && cuenta_b && tarea_tics(a) > 2 && tarea_tics(b) > 2)
        kprint("MULTITAREA OK: 3 tareas turnandose a la vez\n");
    else
        kprint("MULTITAREA FALLA: las tareas no se turnan\n");
    parar_demo = 1;
    fin = timer_tics() + 100;
    while ((tarea_viva(a) || tarea_viva(b)) && timer_tics() < fin) __asm__ volatile ("hlt");
}
"""
_C12 = _C11 + "    demo_multitarea();\n"
_O12 = '    shell_orden("tareas", "las tareas (multitarea)", o_tareas);\n'
_D13 = _D12 + r"""#include "usuario.h"

extern uint8_t usuario_demo_ini[], usuario_demo_fin[], usuario_demo_bueno[], usuario_demo_travieso[];
static int lanzar_demo(uint8_t *entrada, const char *nombre, char *motivo) {
    uint8_t *dst = (uint8_t *)USUARIO_DESDE;                 /* se COPIA a la zona de usuario: ahí sí puede correr */
    uint32_t n = (uint32_t)(usuario_demo_fin - usuario_demo_ini);
    for (uint32_t i = 0; i < n; i++) dst[i] = usuario_demo_ini[i];
    void (*f)(void) = (void (*)(void))(USUARIO_DESDE + (uint32_t)(entrada - usuario_demo_ini));
    int k = usuario_ejecutar(f, USUARIO_HASTA - 16, nombre);
    uint32_t fin = timer_tics() + 300;
    while (k > 0 && tarea_viva(k) && timer_tics() < fin) __asm__ volatile ("hlt");
    if (k > 0 && tarea_viva(k)) tarea_matar(k);
    usuario_ultimo_motivo(motivo, 96);
    return k > 0;
}
static int probar_usuario(void) {
    char m1[96], m2[96];
    int a = lanzar_demo(usuario_demo_bueno, "bueno", m1);
    int b = lanzar_demo(usuario_demo_travieso, "travieso", m2);
    return a && b && m1[0] == 't' && m2[0] == 'l';
}
static void o_usuario(const char *a) {
    (void)a;
    kprint(probar_usuario() ? "Modo usuario: el bueno termina bien y al travieso lo cierra el kernel\n"
                            : "Modo usuario: algo no fue como esperaba\n");
}
static void demo_usuario(void) {
    usuario_init();
    if (probar_usuario()) kprint("MODO USUARIO OK: el bueno termino bien y al travieso lo cerro el kernel\n");
    else kprint("MODO USUARIO FALLA\n");
}
"""
_C13 = _C12 + "    demo_usuario();\n"
_O13 = _O12 + '    shell_orden("usuario", "prueba otra vez el modo usuario", o_usuario);\n'
_D14 = _D13 + r"""#include "programa.h"

static void o_programas(const char *a) { (void)a; programa_listar(); }
static void o_ejecuta(const char *a) {
    if (!*a) { kprint("Dime cual: ejecuta hola\n"); return; }
    char r[128];
    if (!programa_buscar(a, r, sizeof(r))) { kprint("No encuentro el programa "); kprint(a); kputc('\n'); return; }
    programa_ejecutar(r);
}
static void demo_programa(void) {
    char r[128];
    if (!programa_buscar("hola", r, sizeof(r))) {
        kprint("Aun no hay hola.elf en el disco (el taller de Kira lo deja en kira_portatil/kernel/programas)\n");
        return;
    }
    if (programa_ejecutar(r) == 0) kprint("PROGRAMA OK: cargado del disco y ejecutado en modo usuario\n");
}
"""
_C14 = _C13 + "    demo_programa();\n"
_O14 = _O13 + ('    shell_orden("programas", "los programas que hay en el disco", o_programas);\n'
               '    shell_orden("ejecuta", "ejecuta un programa del disco (ejecuta hola)", o_ejecuta);\n')
_D15 = _D14 + r"""#include "red.h"
#include "ip.h"

static void o_red(const char *a) { (void)a; if (ip_dhcp()) ip_ping(); }
static void o_ip(const char *a) { (void)a; ip_info(); }
static void demo_red(void) { if (ip_dhcp()) ip_ping(); }
"""
_C15 = _C14 + "    demo_red();\n"
_O15 = _O14 + ('    shell_orden("red", "pide direccion IP (DHCP) y hace ping al router", o_red);\n'
               '    shell_orden("ip", "mi direccion IP", o_ip);\n')

_K11 = _k_shell("etapa 11: consola propia", _D11, _C11, "")
_K12 = _k_shell("etapa 12: multitarea", _D12, _C12, _O12)
_K13 = _k_shell("etapa 13: modo usuario", _D13, _C13, _O13)
_K14 = _k_shell("etapa 14: programas desde el disco", _D14, _C14, _O14)
_K15 = _k_shell("etapa 15: red con DHCP", _D15, _C15, _O15)

_BASE = {"boot.s": _BOOT, "linker.ld": _LINKER, "io.h": _IO_H, "consola.h": _CONSOLA_H, "consola.c": _CONSOLA_C}
_E2 = {"gdt.c": _GDT_C, "gdt_asm.s": _GDT_S}
_E3 = {"idt.h": _IDT_H, "idt.c": _IDT_C, "isr.s": _ISR_S}
_E4 = {"pic.c": _PIC_C, "timer.c": _TIMER_C, "timer.h": _TIMER_H, "teclado.c": _TECLADO_C}
_E5 = {"memoria.h": _MEMORIA_H, "memoria.c": _MEMORIA_C}
_E6 = {"pci.h": _PCI_H, "pci.c": _PCI_C}
_E7 = {"disco.h": _DISCO_H, "disco.c": _DISCO_C}
_E8 = {"red.h": _RED_H, "red.c": _RED_C}
_E9 = {"ahci.h": _AHCI_H, "ahci.c": _AHCI_C}
_E10 = {"ahci.h": _AHCI2_H, "ahci.c": _AHCI2_C, "ext4.h": _EXT4_H, "ext4.c": _EXT4_C}
_E11 = {"consola.h": _CONSOLA2_H, "consola.c": _CONSOLA2_C, "teclado.h": _TECLADO_H, "teclado.c": _TECLADO2_C,
        "shell.h": _SHELL_H, "shell.c": _SHELL_C}
_E12 = {"idt.h": _IDT2_H, "idt.c": _IDT2_C, "isr.s": _ISR2_S, "tareas.h": _TAREAS_H, "tareas.c": _TAREAS_C}
_E13 = {"gdt.c": _GDT2_C, "usuario.h": _USUARIO_H, "usuario.c": _USUARIO_C, "usuario_demo.s": _USUARIO_DEMO_S}
_E14 = {"programa.h": _PROGRAMA_H, "programa.c": _PROGRAMA_C}
_E15 = {"red.h": _RED2_H, "red.c": _RED2_C, "ip.h": _IP_H, "ip.c": _IP_C}


def _junta(*partes):
    d = {}
    for p in partes:
        d.update(p)
    return d


ETAPAS = [
    {"n": 1, "titulo": "Arranque: el kernel arranca y saluda",
     "que": "Multiboot, pila, kernel_main en C, pantalla VGA y puerto serie.",
     "claves": "arranque arrancar saludo hola multiboot pantalla vga serie empezar base minimo",
     "espera": ["Hola desde mi SO!", "Multiboot OK", "KERNEL_LISTO"],
     "archivos": _junta(_BASE, {"kernel.c": _K1})},
    {"n": 2, "titulo": "GDT: segmentos propios (modelo plano)",
     "que": "Tabla de descriptores global con código y datos del kernel; lgdt y salto lejano.",
     "claves": "gdt segmentos segmento descriptores descriptor global modo protegido lgdt",
     "espera": ["GDT OK", "KERNEL_LISTO"],
     "archivos": _junta(_BASE, _E2, {"kernel.c": _K2})},
    {"n": 3, "titulo": "IDT: excepciones del procesador",
     "que": "Tabla de interrupciones, 48 entradas en ensamblador, manejador en C con el nombre de cada excepción.",
     "claves": "idt interrupciones interrupcion excepciones excepcion isr manejador lidt fallos",
     "espera": ["GDT OK", "IDT OK", "punto de ruptura", "Excepciones OK", "KERNEL_LISTO"],
     "archivos": _junta(_BASE, _E2, _E3, {"kernel.c": _K3})},
    {"n": 4, "titulo": "PIC, temporizador y teclado",
     "que": "Remapear el PIC, PIT a 100 Hz contando tics, teclado PS/2 que escribe en pantalla.",
     "claves": "pic irq irqs temporizador timer pit reloj tics teclado tecla teclas keyboard",
     "espera": ["IDT OK", "PIC OK", "Teclado OK", "TIMER OK", "KERNEL_LISTO"],
     "archivos": _junta(_BASE, _E2, _E3, _E4, {"kernel.c": _K4})},
    {"n": 5, "titulo": "Memoria: marcos, paginación y heap",
     "que": "Mapa de bits de marcos de 4 KB, paginación con mapa identidad de 16 MB y kmalloc/kfree.",
     "claves": "memoria marcos marco paginacion paginas pagina heap kmalloc malloc kfree reservar mapa bits",
     "espera": ["MARCOS OK", "PAGINACION OK", "HEAP OK", "KERNEL_LISTO"],
     "archivos": _junta(_BASE, _E2, _E3, _E4, _E5, {"kernel.c": _K5})},
    {"n": 6, "titulo": "PCI: qué aparatos tiene el ordenador",
     "que": "Recorrer el bus PCI y decir cada aparato (disco, red, gráfica, USB…) con su fabricante y clase.",
     "claves": "pci bus aparatos dispositivos hardware detectar listar descubrir enumerar",
     "espera": ["PCI OK", "KERNEL_LISTO"],
     "archivos": _junta(_BASE, _E2, _E3, _E4, _E5, _E6, {"kernel.c": _K6})},
    {"n": 7, "titulo": "Driver de disco ATA (leer y escribir sectores)",
     "que": "Disco por PIO: identificarlo y leer/escribir sectores. Solo escribe en el disco de pruebas (firma KIRADISK).",
     "claves": "disco discos ata ide sector sectores leer escribir almacenamiento duro driver",
     "espera": ["DISCO OK: leo y escribo", "KERNEL_LISTO"],
     "archivos": _junta(_BASE, _E2, _E3, _E4, _E5, _E6, _E7, {"kernel.c": _K7})},
    {"n": 8, "titulo": "Driver de red e1000 (enviar y recibir)",
     "que": "Tarjeta Intel e1000: MAC, colas de envío/recepción y un ARP al router virtual (red aislada de QEMU).",
     "claves": "red tarjeta ethernet e1000 internet paquetes tramas arp mac network enviar recibir",
     "espera": ["Red: tarjeta e1000", "RED OK", "KERNEL_LISTO"],
     "archivos": _junta(_BASE, _E2, _E3, _E4, _E5, _E6, _E7, _E8, {"kernel.c": _K8})},
    {"n": 9, "titulo": "Driver AHCI de solo lectura (disco SATA)",
     "que": "El disco de los portátiles modernos: identificarlo y leer su tabla de particiones (MBR o GPT). Nunca escribe.",
     "claves": "ahci sata particiones particion gpt mbr disco duro portatil real lectura driver",
     "espera": ["AHCI OK", "Tabla MBR", "Tabla GPT", "KERNEL_LISTO"],
     "archivos": _junta(_BASE, _E2, _E3, _E4, _E5, _E6, _E7, _E8, _E9, {"kernel.c": _K9})},
    {"n": 10, "titulo": "Sistema de archivos ext4 (solo lectura)",
     "que": "Leer la particion Linux: superbloque, grupos, inodos, extents y carpetas. Listar / y abrir archivos.",
     "claves": "ext4 archivos archivo carpetas carpeta sistema leer ficheros fichero inodos extents",
     "espera": ["EXT4: particion Linux", "Hola desde el disco de Kira", "EXT4 OK", "KERNEL_LISTO"],
     "archivos": _junta(_BASE, _E2, _E3, _E4, _E5, _E6, _E7, _E8, _E9, _E10, {"kernel.c": _K10})},
    {"n": 11, "titulo": "Consola propia (kira>)",
     "que": "Una consola con ordenes: ayuda, ls, cd, cat, aparatos, discos, memoria, tiempo, reiniciar.",
     "claves": "consola shell terminal ordenes comandos escribir prompt interprete",
     "espera": ["KERNEL_LISTO", "kira:", "Ordenes:", "Hola desde el disco de Kira", "Memoria libre"],
     "entrada": "ayuda\nls /\ncat kira\nmemoria\n",
     "archivos": _junta(_BASE, _E2, _E3, _E4, _E5, _E6, _E7, _E8, _E9, _E10, _E11, {"kernel.c": _K11})},
    {"n": 12, "titulo": "Multitarea (varias tareas a la vez)",
     "que": "Cambio de contexto en cada tic del reloj y planificador por turnos; orden tareas.",
     "claves": "multitarea tareas procesos planificador contexto hilos turnos concurrencia",
     "espera": ["MULTITAREA OK", "KERNEL_LISTO", "kira:", "contador A"],
     "entrada": "tareas\n",
     "archivos": _junta(_BASE, _E2, _E3, _E4, _E5, _E6, _E7, _E8, _E9, _E10, _E11, _E12, {"kernel.c": _K12})},
    {"n": 13, "titulo": "Modo usuario y llamadas al sistema",
     "que": "TSS, segmentos de usuario, int 0x80; un programa que intenta algo prohibido y el kernel lo cierra.",
     "claves": "usuario anillo ring tss llamadas sistema syscall proteccion privilegios",
     "espera": ["Hola desde el modo usuario (anillo 3)", "lo cierro. El sistema sigue.", "MODO USUARIO OK",
                "KERNEL_LISTO", "kira:"],
     "entrada": "usuario\n",
     "archivos": _junta(_BASE, _E2, _E3, _E4, _E5, _E6, _E7, _E8, _E9, _E10, _E11, _E12, _E13, {"kernel.c": _K13})},
    {"n": 14, "titulo": "Programas desde el disco (ELF)",
     "que": "Cargar un programa ELF del disco y ejecutarlo en modo usuario (ejecuta hola).",
     "claves": "programas programa elf ejecutar cargar aplicaciones binario lanzar",
     "espera": ["Hola desde un programa cargado del disco", "PROGRAMA OK", "KERNEL_LISTO", "kira:"],
     "entrada": "programas\n",
     "archivos": _junta(_BASE, _E2, _E3, _E4, _E5, _E6, _E7, _E8, _E9, _E10, _E11, _E12, _E13, _E14, {"kernel.c": _K14})},
    {"n": 15, "titulo": "Red: IP, UDP y DHCP (en QEMU)",
     "que": "Pila de red sobre la e1000: DHCP para tener direccion IP y ping al router (red aislada de QEMU).",
     "claves": "dhcp ip udp icmp ping pila tcp direccion internet protocolo",
     "espera": ["DHCP OK", "KERNEL_LISTO", "kira:"],
     "entrada": "ip\n",
     "archivos": _junta(_BASE, _E2, _E3, _E4, _E5, _E6, _E7, _E8, _E9, _E10, _E11, _E12, _E13, _E14, _E15, {"kernel.c": _K15})},
]

SIGUIENTES = ("pantalla gráfica (dibujar píxeles)", "escribir en un disco propio (sistema de archivos con escritura)",
              "TCP y un navegador de texto", "driver de la red por cable Broadcom (necesita probarse en el portátil)",
              "USB (teclado y pendrives)", "sonido")


def etapa(n):
    for e in ETAPAS:
        if e["n"] == int(n):
            return e
    return None


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def etapa_para(tarea):
    """La etapa cuya plantilla resuelve lo pedido («añade la GDT» → 2, «el teclado» → 4), o None. Puro."""
    palabras = set(re.findall(r"[a-z0-9]+", _norm(tarea)))
    mejor, puntos = None, 0
    for e in ETAPAS[1:]:                         # la 1 es la base: no la «resuelve» un pedido
        p = len(palabras & set(e["claves"].split()))
        if p > puntos:
            mejor, puntos = e, p
    return mejor if puntos else None


def fichas_para(tarea, n=2):
    """Las fichas que más tienen que ver con lo pedido (para dárselas al cerebro). Puro."""
    palabras = set(w for w in re.findall(r"[a-z0-9]+", _norm(tarea)) if len(w) > 2)
    puntuadas = []
    for tema, texto in CONCEPTOS:
        pal = set(re.findall(r"[a-z0-9]+", _norm(tema + " " + texto)))
        puntuadas.append((len(palabras & pal), tema, texto))
    puntuadas.sort(key=lambda x: -x[0])
    return [(t, x) for p, t, x in puntuadas[:n] if p > 0]


def texto_etapas(actual=0):
    lineas = ["Etapas de mi kernel (plantillas probadas):"]
    for e in ETAPAS:
        marca = "✓" if e["n"] <= actual else " "
        lineas.append(f" [{marca}] {e['n']}. {e['titulo']} — {e['que']}")
    lineas.append("Después vendrían (aún sin plantilla, las programaríamos juntas): " + "; ".join(SIGUIENTES) + ".")
    lineas.append("Di «pon la etapa N del kernel» o «programa el kernel: <lo que quieras>».")
    return "\n".join(lineas)
