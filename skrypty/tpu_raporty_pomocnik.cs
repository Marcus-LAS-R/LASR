// Las-R: pomocnik "Zestawienia raportów TPU" - woła bibliotekę raportów
// Taksatora PU (ReportsHelper.dll) bez otwierania Taksatora.
//
// Kompilowany przez wtyczkę (tpu_raporty_pliki.kompiluj_pomocnika) kompilatorem
// .NET Framework 4 z Windows (csc.exe, C# 5 - bez nowszej składni), x64.
// Działa w osobnej domenie aplikacji z katalogiem i konfiguracją Taksatora
// (ApplicationBase = katalog Taksatora, TaksatorPU.exe.config) - biblioteki,
// przekierowania wersji i wzorzec TaksatorPU.dat jak w samym Taksatorze.
//
// Użycie (wyjście UTF-8, jedna linia = jeden komunikat, pola rozdzielone TAB):
//   tpu_raporty.exe <katalog Taksatora> lista
//       -> RAPORT <id> <nazwa>
//   tpu_raporty.exe <katalog Taksatora> wersja <baza.mdb>
//       -> WERSJA <wersja bazy> <wersja wymagana>
//   tpu_raporty.exe <katalog Taksatora> aktualizuj <baza.mdb>
//       -> WERSJA <przed> <po>      (TYLKO na kopii bazy!)
//   tpu_raporty.exe <katalog Taksatora> raporty <baza.mdb> <plik zadań>
//       plik zadań (UTF-8): linie "<nr>\t<id raportu>\t<obręb>\t<plik .xls>"
//       -> OK <nr> | BLAD <nr> <opis>
// Błąd ogólny: BLAD - <opis>, kod wyjścia 1. Baza bez hasła (wtyczka podaje
// kopię skompaktowaną bez hasła).
using System;
using System.IO;
using System.Reflection;
using System.Text;

public class TpuRaporty : MarshalByRefObject
{
    const string Domena = "LasR_TPU";
    const BindingFlags Wszystkie = BindingFlags.Public | BindingFlags.NonPublic |
        BindingFlags.Instance | BindingFlags.Static;

    static int Main(string[] a)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        if (a.Length < 2)
        {
            Console.WriteLine("BLAD\t-\tza mało argumentów");
            return 1;
        }
        string kat = a[0];
        if (!File.Exists(Path.Combine(kat, "ReportsHelper.dll")))
        {
            Console.WriteLine("BLAD\t-\tbrak ReportsHelper.dll w " + kat);
            return 1;
        }
        var setup = new AppDomainSetup();
        setup.ApplicationBase = kat;
        setup.ConfigurationFile = Path.Combine(kat, "TaksatorPU.exe.config");
        var dom = AppDomain.CreateDomain(Domena, null, setup);
        try
        {
            var p = (TpuRaporty)dom.CreateInstanceFromAndUnwrap(
                Assembly.GetExecutingAssembly().Location,
                typeof(TpuRaporty).FullName);
            return p.Wykonaj(a);
        }
        catch (Exception e)
        {
            Console.WriteLine("BLAD\t-\t" + Opis(e));
            return 1;
        }
    }

    static string Opis(Exception e)
    {
        while (e.InnerException != null) e = e.InnerException;
        return (e.Message ?? e.GetType().Name).Replace("\r", " ")
            .Replace("\n", " ").Replace("\t", " ").Trim();
    }

    string kat;
    Assembly reports;

    public int Wykonaj(string[] a)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        kat = a[0];
        Environment.CurrentDirectory = kat;
        reports = Assembly.LoadFrom(Path.Combine(kat, "ReportsHelper.dll"));
        try
        {
            switch (a[1])
            {
                case "lista": return Lista();
                case "wersja": return Wersja(a[2], false);
                case "aktualizuj": return Wersja(a[2], true);
                case "raporty": return Raporty(a[2], a[3]);
            }
            Console.WriteLine("BLAD\t-\tnieznane polecenie " + a[1]);
            return 1;
        }
        catch (Exception e)
        {
            Console.WriteLine("BLAD\t-\t" + Opis(e));
            return 1;
        }
    }

    int Lista()
    {
        var t = reports.GetType("ReportsHelper.ExternalMethods");
        foreach (string s in (string[])t.GetMethod("GetReportList")
                 .Invoke(null, null))
        {
            int i = s.IndexOf('-');
            if (i < 0) continue;
            Console.WriteLine("RAPORT\t" + s.Substring(0, i).Trim() + "\t" +
                              s.Substring(i + 1).Trim());
        }
        return 0;
    }

    // Wersja bazy (V_PARAMETER.db_ver) i aktualizacja struktury procedurą
    // Taksatora (ForesTaxDBUpdate.UpdateDB - jak przy otwieraniu bazy
    // w Taksatorze). Konstruktor QuietMode sam sprawdza wersję, więc obiekt
    // powstaje bez konstruktora - tylko do podłączenia bazy.
    int Wersja(string baza, bool aktualizuj)
    {
        var q = reports.GetType("ReportsHelper.QuietMode");
        object o = System.Runtime.Serialization.FormatterServices
            .GetUninitializedObject(q);
        var init = q.GetMethod("InitializeDataBase", Wszystkie, null,
            new[] { typeof(string), typeof(string), typeof(string) }, null);
        if (!(bool)init.Invoke(o, new object[] { baza, "", "" }))
        {
            Console.WriteLine("BLAD\t-\tnie udało się podłączyć bazy");
            return 1;
        }
        var u = Assembly.LoadFrom(Path.Combine(kat,
            "TaxusSI.ForesTax.Data.dll"))
            .GetType("TaxusSI.ForesTax.Data.ForesTaxDBUpdate");
        object inst = u.GetProperty("Instance").GetValue(null, null);
        var bm = u.GetProperty("BaseManager");
        if (bm.GetValue(inst, null) == null)
        {
            var f = q.GetField("m_baseManager", Wszystkie);
            if (f != null) bm.SetValue(inst, f.GetValue(o), null);
        }
        object przed = u.GetProperty("DBVersion").GetValue(inst, null);
        object wymagana = u.GetField("CurrentDBVersion", Wszystkie)
            .GetValue(null);
        if (!aktualizuj)
        {
            Console.WriteLine("WERSJA\t" + przed + "\t" + wymagana);
            return 0;
        }
        // procedura szuka wzorców TaksatorPU*.dat obok pliku .exe procesu
        string exe = Path.GetDirectoryName(System.Diagnostics.Process
            .GetCurrentProcess().MainModule.FileName);
        foreach (string dat in Directory.GetFiles(kat, "TaksatorPU*.dat"))
        {
            string cel = Path.Combine(exe, Path.GetFileName(dat));
            if (!File.Exists(cel) ||
                new FileInfo(cel).Length != new FileInfo(dat).Length ||
                File.GetLastWriteTimeUtc(cel) != File.GetLastWriteTimeUtc(dat))
                File.Copy(dat, cel, true);
        }
        u.GetMethod("UpdateDB", new Type[0]).Invoke(inst, null);
        Console.WriteLine("WERSJA\t" + przed + "\t" +
                          u.GetProperty("DBVersion").GetValue(inst, null));
        return 0;
    }

    int Raporty(string baza, string plikZadan)
    {
        var t = reports.GetType("ReportsHelper.ExternalMethods");
        var run = t.GetMethod("RunReport", new[] {
            typeof(int), typeof(string), typeof(string), typeof(string) });
        int bledy = 0;
        foreach (string linia in File.ReadAllLines(plikZadan, Encoding.UTF8))
        {
            if (linia.Trim().Length == 0) continue;
            string[] p = linia.Split('\t');
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(p[3]));
                run.Invoke(null, new object[] { int.Parse(p[1]), p[2], p[3],
                                                baza });
                if (!File.Exists(p[3]))
                    throw new Exception("raport nie utworzył pliku");
                Console.WriteLine("OK\t" + p[0]);
            }
            catch (Exception e)
            {
                bledy++;
                Console.WriteLine("BLAD\t" + p[0] + "\t" + Opis(e));
            }
            Console.Out.Flush();
        }
        return bledy == 0 ? 0 : 2;
    }
}
