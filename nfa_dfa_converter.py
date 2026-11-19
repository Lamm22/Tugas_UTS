#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nfa_dfa_converter.py
====================
Program CLI (text-based, jalan di terminal) untuk materi:
  Teori Bahasa dan Automata - Konversi NFA ke DFA (Subset Construction).

Fitur:
  1. Menampilkan tabel transisi NFA.
  2. Menguji string pada NFA (simulasi nondeterministik - melacak himpunan state).
  3. Mengkonversi NFA -> DFA dengan algoritma Subset Construction,
     dan menampilkan SETIAP LANGKAH prosesnya.
     - Mode langkah: tekan Enter tiap state (interaktif), atau tampilkan sekaligus.
  4. Menampilkan tabel transisi DFA hasil + pemetaan nama state (A={...}) + state akhir.
  5. Menguji string pada DFA hasil (simulasi deterministik - satu jalur).

Tema: output berwarna (ANSI) saat jalan interaktif di terminal modern.

Catatan:
  - NFA pada program ini TIDAK memakai epsilon-transition,
    sehingga epsilon-closure tidak diterapkan.
  - State DFA diberi nama A, B, C, ... sesuai URUTAN DITEMUKAN (BFS).

Jalankan:  python nfa_dfa_converter.py
"""

import sys
import re
from collections import deque


# ============================================================
#  TEMA WARNA (ANSI)
# ============================================================

class C:
    """Kode warna ANSI."""
    R = "\033[0m"     # reset
    B = "\033[1m"     # bold
    DIM = "\033[2m"   # redup
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    AMBER = "\033[93m"
    MAG = "\033[95m"


# Hanya pakai warna jika stdout adalah terminal (bukan pipe/redirect),
# supaya output yang dialihkan tetap bersih tanpa kode escape.
USE_COLOR = sys.stdout.isatty()


def c(text, code):
    """Bungkus teks dengan warna (bila USE_COLOR)."""
    if USE_COLOR:
        return f"{code}{text}{C.R}"
    return text


def _enable_ansi_windows():
    """Aktifkan pemrosesan ANSI VT pada Windows console."""
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VT_PROCESSING
    except Exception:
        pass


# ============================================================
#  UTILITAS
# ============================================================

def state_key(s):
    """Kunci pengurutan state agar q0,q1,q2,...,q10 tampil berurut rapi."""
    m = re.match(r"^([A-Za-z_]+)(\d+)$", s)
    if m:
        return (m.group(1), int(m.group(2)))
    return (s, 0)


def fmt_set(s):
    """Format himpunan state -> '{q0,q1}'; himpunan kosong -> '∅'."""
    if not s:
        return "∅"
    return "{" + ",".join(sorted(s, key=state_key)) + "}"


def label(idx):
    """Buat nama state DFA: 0->A, 1->B, ..., 25->Z, 26->AA, ..."""
    name = ""
    n = idx + 1
    while n > 0:
        n, r = divmod(n - 1, 26)
        name = chr(ord("A") + r) + name
    return name


def print_table(headers, rows, widths):
    """Cetak tabel sederhana dengan lebar kolom tetap (header berwarna redup)."""
    def fmt_row(r):
        return " | ".join(str(cel).ljust(widths[i]) for i, cel in enumerate(r))
    print(c(fmt_row(headers), C.DIM + C.B))
    print("-+-".join("-" * w for w in widths))
    for r in rows:
        print(fmt_row(r))


# ============================================================
#  KELAS MESIN
# ============================================================

class NFA:
    """NFA tanpa epsilon-transition.

    transitions: dict {(state, symbol): set(state)}.
    delta(state, symbol) mengembalikan set (bisa kosong).
    """

    def __init__(self, states, alphabet, transitions, start, finals):
        self.states = sorted(set(states), key=state_key)
        self.alphabet = list(alphabet)
        self.transitions = transitions
        self.start = start
        self.finals = set(finals)

    def delta(self, state, symbol):
        return self.transitions.get((state, symbol), set())


class DFA:
    """DFA hasil Subset Construction. Tiap state = frozenset dari state NFA."""

    def __init__(self, name_of, order, alphabet, start, transitions, finals):
        self.name_of = name_of        # dict frozenset -> huruf
        self.order = order            # list frozenset (urutan ditemukan)
        self.alphabet = alphabet
        self.start = start            # frozenset
        self.transitions = transitions  # dict (frozenset, sym) -> frozenset
        self.finals = finals          # list frozenset

    def name(self, fs):
        return self.name_of.get(fs, "?")

    def is_final(self, fs):
        return fs in set(self.finals)


# ============================================================
#  KONVERSI: SUBSET CONSTRUCTION
# ============================================================

def subset_construction(nfa, verbose=True, step=False):
    """Konversi NFA ke DFA. Mengembalikan objek DFA.

    Algoritma:
      - State awal DFA = {q0}.
      - Untuk tiap state DFA S yang belum diproses, dan tiap simbol a:
          U = gabungan delta(q,a) untuk semua q dalam S.
          Jika U belum jadi state DFA, daftarkan & antrikan.
          Transisi DFA: delta_DFA(S,a) = U.
      - State DFA final jika memuat >= 1 state akhir NFA.

    step=True  -> jeda tiap state (tekan Enter), 's' untuk tampilkan sisanya.
    """
    if verbose:
        print()
        print(c("=== KONVERSI NFA -> DFA (Subset Construction) ===", C.CYAN + C.B))
        print(c("Ide utama: satu state DFA = satu himpunan state NFA.", C.DIM))
        print()

    name_of = {}
    order = []

    def get_name(fs):
        if fs not in name_of:
            name_of[fs] = label(len(name_of))
            order.append(fs)
        return name_of[fs]

    start_set = frozenset([nfa.start])
    get_name(start_set)

    queue = deque([start_set])
    processed = set()
    dfa_trans = {}

    if verbose:
        print(f"State awal DFA: {c(name_of[start_set], C.AMBER + C.B)} = {fmt_set(set(start_set))}")
        print(c(f"Antrian untuk diproses: [{name_of[start_set]}]", C.DIM))
        print()

    while queue:
        S = queue.popleft()
        if S in processed:
            continue
        processed.add(S)

        if verbose:
            print(c(f"[Proses {name_of[S]} = {fmt_set(set(S))}]", C.B))

        for a in nfa.alphabet:
            parts = []
            U = set()
            for q in sorted(S, key=state_key):
                tq = nfa.delta(q, a)
                U |= tq
                parts.append(f"δ({q},{a})={fmt_set(tq)}")
            Uf = frozenset(U)
            dfa_trans[(S, a)] = Uf
            is_new = Uf not in name_of
            nm = get_name(Uf)
            if is_new:
                queue.append(Uf)
            if verbose:
                union_str = " ∪ ".join(parts) if parts else "∅"
                if is_new:
                    tag = c("[baru]", C.GREEN + C.B)
                else:
                    tag = c("[sudah ada]", C.DIM)
                tgt = c(nm, C.CYAN + C.B)
                print(f"  simbol '{a}': {union_str}  ->  {fmt_set(set(Uf))} = {tgt} {tag}")
                if is_new:
                    print(c(f"    -> {nm} ditambahkan ke antrian", C.DIM))

        if verbose:
            t = ", ".join(f"δ({name_of[S]},{a})={name_of[dfa_trans[(S,a)]]}"
                          for a in nfa.alphabet)
            print(c(f"  Transisi DFA: {t}", C.DIM))
            qstr = ", ".join(name_of[x] for x in queue)
            print(c(f"  Antrian sekarang: [{qstr}]", C.DIM))

        if verbose and step:
            ans = input(c("\n  [Enter] lanjut   (s = tampilkan semua sisanya) > ", C.DIM))
            if ans.strip().lower() == "s":
                step = False
                print()
            print()

    finals = [S for S in order if set(S) & nfa.finals]
    dfa = DFA(name_of, order, nfa.alphabet, start_set, dfa_trans, finals)

    if verbose:
        print(c("Selesai.", C.CYAN + C.B))
        print(f"State akhir NFA: {fmt_set(nfa.finals)}")
        fs = ", ".join(name_of[S] for S in finals)
        print("State akhir DFA (memuat state akhir NFA): "
              + c(f"F_DFA = {{{fs}}}", C.AMBER + C.B))
        print()
    return dfa


# ============================================================
#  TAMPILAN TABEL
# ============================================================

def print_nfa_table(nfa):
    print()
    print(c("=== TABEL TRANSISI NFA ===", C.CYAN + C.B))
    headers = ["State"] + [f"Input {a}" for a in nfa.alphabet]
    rows = []
    for q in nfa.states:
        rows.append([q] + [fmt_set(nfa.delta(q, a)) for a in nfa.alphabet])
    widths = [6] + [12] * len(nfa.alphabet)
    print_table(headers, rows, widths)
    print(f"State awal : {c(nfa.start, C.CYAN + C.B)}")
    print(f"State akhir: {c(fmt_set(nfa.finals), C.AMBER + C.B)}")


def print_dfa_table(dfa):
    print()
    print(c("=== TABEL TRANSISI DFA ===", C.CYAN + C.B))
    headers = ["State"] + [f"Input {a}" for a in dfa.alphabet] + ["Set NFA", "Final"]
    rows = []
    for S in dfa.order:
        nm = dfa.name_of[S]
        row = [nm] + [dfa.name_of[dfa.transitions[(S, a)]] for a in dfa.alphabet]
        finalmark = c("YA", C.AMBER + C.B) if dfa.is_final(S) else ""
        row += [fmt_set(set(S)), finalmark]
        rows.append(row)
    widths = [6] + [10] * len(dfa.alphabet) + [16, 6]
    print_table(headers, rows, widths)
    print(f"State awal DFA : {c(dfa.name_of[dfa.start], C.CYAN + C.B)}")
    fs = ", ".join(dfa.name_of[S] for S in dfa.finals)
    print("State akhir DFA: {" + c(fs, C.AMBER + C.B) + "}")


# ============================================================
#  UJI STRING
# ============================================================

def test_string_nfa(nfa, s):
    print()
    print(c(f'Menguji string "{s if s != "" else "ε"}" pada NFA ...', C.CYAN + C.B))
    cur = {nfa.start}
    print(f"Langkah 0 (start): {fmt_set(cur)}")
    for a in s:
        parts = []
        nxt = set()
        for q in sorted(cur, key=state_key):
            tq = nfa.delta(q, a)
            nxt |= tq
            parts.append(f"δ({q},{a})={fmt_set(tq)}")
        print(f"Baca '{a}': " + " ∪ ".join(parts) + f"  ->  {fmt_set(nxt)}")
        cur = nxt
    inter = cur & nfa.finals
    if inter:
        print(f"Himpunan akhir {fmt_set(cur)} ∩ final {fmt_set(nfa.finals)} "
              f"= {fmt_set(inter)}  ->  " + c("DITERIMA", C.GREEN + C.B))
    else:
        print(f"Himpunan akhir {fmt_set(cur)} ∩ final {fmt_set(nfa.finals)} "
              f"= ∅  ->  " + c("DITOLAK", C.RED + C.B))


def test_string_dfa(dfa, s):
    print()
    print(c(f'Menguji string "{s if s != "" else "ε"}" pada DFA ...', C.CYAN + C.B))
    cur = dfa.start
    names = [dfa.name_of[cur]]
    for a in s:
        cur = dfa.transitions[(cur, a)]
        names.append(dfa.name_of[cur])
    parts = [names[0]]
    for i, a in enumerate(s):
        parts.append(f"--{a}-->")
        parts.append(names[i + 1])
    print("Lintasan: " + " ".join(parts))
    print(f"Berakhir di state {c(dfa.name_of[cur], C.CYAN + C.B)} = {fmt_set(set(cur))}")
    if dfa.is_final(cur):
        print(f"{dfa.name_of[cur]} adalah state akhir DFA  ->  " + c("DITERIMA", C.GREEN + C.B))
    else:
        print(f"{dfa.name_of[cur]} BUKAN state akhir DFA  ->  " + c("DITOLAK", C.RED + C.B))


# ============================================================
#  INPUT MANUAL
# ============================================================

def input_manual():
    print()
    print(c("-- INPUT NFA MANUAL --", C.MAG + C.B))
    states = [s.strip() for s in input("State (pisah koma, cth q0,q1,q2): ").split(",") if s.strip()]
    alphabet = [s.strip() for s in input("Alfabet (pisah koma, cth 0,1): ").split(",") if s.strip()]
    start = input("State awal: ").strip()
    finals = set(s.strip() for s in input("State akhir (pisah koma): ").split(",") if s.strip())
    trans = {}
    print("\nIsi transisi (kosongkan untuk ∅):")
    for q in states:
        for a in alphabet:
            t = input(f"  δ({q},{a}) -> tujuan (pisah koma): ").strip()
            if t:
                tgt = set(s.strip() for s in t.split(",") if s.strip())
                # validasi sederhana
                bad = tgt - set(states)
                if bad:
                    print(c(f"    ! peringatan: {bad} bukan state yang dikenal", C.AMBER + C.B))
                trans[(q, a)] = tgt
    return NFA(states, alphabet, trans, start, finals)


# ============================================================
#  MENU UTAMA
# ============================================================

def choose_nfa():
    while True:
        print()
        print(c("=" * 58, C.CYAN))
        print(c("   NFA -> DFA CONVERTER  (Subset Construction)", C.CYAN + C.B))
        print(c("=" * 58, C.CYAN))
        print("   1. Input NFA manual")
        print("   0. Keluar")
        c0 = input("Pilih: ").strip()
        if c0 == "1":
            return input_manual()
        if c0 == "0":
            return None
        print(c("Pilihan tidak dikenal.", C.AMBER + C.B))


def run_menu(nfa):
    dfa = None
    while True:
        print()
        print(c("--- MENU ---", C.CYAN + C.B))
        print("   1. Tampilkan tabel transisi NFA")
        print("   2. Uji string pada NFA")
        print("   3. Konversi NFA -> DFA (langkah-demi-langkah)")
        print("   4. Tampilkan tabel transisi DFA" + (" [belum ada]" if dfa is None else ""))
        print("   5. Uji string pada DFA hasil")
        print("   9. Ganti / input NFA lain")
        print("   0. Keluar")
        c0 = input("Pilih: ").strip()
        if c0 == "1":
            print_nfa_table(nfa)
        elif c0 == "2":
            s = input("String uji (kosongkan untuk ε): ")
            test_string_nfa(nfa, s)
        elif c0 == "3":
            step = input("Mode langkah (tekan Enter per state)? [y/N]: ").strip().lower() == "y"
            dfa = subset_construction(nfa, verbose=True, step=step)
            print_dfa_table(dfa)
        elif c0 == "4":
            if dfa is None:
                print(c("Lakukan konversi dulu (menu 3).", C.AMBER + C.B))
            else:
                print_dfa_table(dfa)
        elif c0 == "5":
            if dfa is None:
                dfa = subset_construction(nfa, verbose=False)
            s = input("String uji (kosongkan untuk ε): ")
            test_string_dfa(dfa, s)
        elif c0 == "9":
            return "again"
        elif c0 == "0":
            return "quit"
        else:
            print(c("Pilihan tidak dikenal.", C.AMBER + C.B))


def main():
    # pastikan karakter unicode (∅ δ ∪ →) & warna ANSI tampil di Windows console
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    _enable_ansi_windows()

    while True:
        nfa = choose_nfa()
        if nfa is None:
            print(c("Sampai jumpa!", C.CYAN + C.B))
            break
        print()
        print(c("NFA dimuat:", C.MAG + C.B))
        print(f"   States : {fmt_set(set(nfa.states))}")
        print(f"   Alfabet: {fmt_set(set(nfa.alphabet))}")
        print(f"   Awal   : {c(nfa.start, C.CYAN + C.B)}")
        print(f"   Akhir  : {c(fmt_set(nfa.finals), C.AMBER + C.B)}")
        res = run_menu(nfa)
        if res == "quit":
            print(c("Sampai jumpa!", C.CYAN + C.B))
            break


if __name__ == "__main__":
    main()
