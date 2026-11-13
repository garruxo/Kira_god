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

static void serie_init(void) {
    outb(COM1 + 1, 0x00);    /* sin interrupciones */
    outb(COM1 + 3, 0x80);    /* DLAB para poner la velocidad */
    outb(COM1 + 0, 0x03);    /* 38400 baudios */
    outb(COM1 + 1, 0x00);
    outb(COM1 + 3, 0x03);    /* 8 bits, sin paridad, 1 de parada */
    outb(COM1 + 2, 0xC7);    /* FIFO */
    outb(COM1 + 4, 0x0B);
}

static void serie_putc(char c) {
    while ((inb(COM1 + 5) & 0x20) == 0) { }
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
    kprint("Escribe algo: ");
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
    kprint("Escribe algo: ");
    for (;;) __asm__ volatile ("hlt");
}
"""

_BASE = {"boot.s": _BOOT, "linker.ld": _LINKER, "io.h": _IO_H, "consola.h": _CONSOLA_H, "consola.c": _CONSOLA_C}
_E2 = {"gdt.c": _GDT_C, "gdt_asm.s": _GDT_S}
_E3 = {"idt.h": _IDT_H, "idt.c": _IDT_C, "isr.s": _ISR_S}
_E4 = {"pic.c": _PIC_C, "timer.c": _TIMER_C, "timer.h": _TIMER_H, "teclado.c": _TECLADO_C}
_E5 = {"memoria.h": _MEMORIA_H, "memoria.c": _MEMORIA_C}


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
]

SIGUIENTES = ("multitarea (cambio de contexto y planificador)", "modo usuario con TSS y llamadas al sistema",
              "initrd y un sistema de archivos sencillo", "una shell propia")


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
