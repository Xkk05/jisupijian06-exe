using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Security.Cryptography;

namespace JisuPijianUpdater
{
    internal static class Program
    {
        private static int Main(string[] args)
        {
            try
            {
                Dictionary<string, string> parsed = ParseArgs(args);
                string url = Required(parsed, "url");
                string appDir = Path.GetFullPath(Required(parsed, "dir"));
                string exeName = Required(parsed, "exe");
                int pid = parsed.ContainsKey("pid") ? int.Parse(parsed["pid"]) : 0;
                string expectedHash = parsed.ContainsKey("hash") ? parsed["hash"] : "";

                Directory.CreateDirectory(appDir);
                string tempDir = Path.Combine(Path.GetTempPath(), "jisupijian_update_" + Guid.NewGuid().ToString("N"));
                Directory.CreateDirectory(tempDir);

                try
                {
                    string packagePath = Path.Combine(tempDir, "update.zip");
                    using (WebClient client = new WebClient())
                    {
                        client.DownloadFile(url, packagePath);
                    }

                    if (!string.IsNullOrWhiteSpace(expectedHash))
                    {
                        string actualHash = Sha256File(packagePath);
                        if (!string.Equals(actualHash, expectedHash, StringComparison.OrdinalIgnoreCase))
                        {
                            throw new InvalidOperationException("Update package hash mismatch.");
                        }
                    }

                    WaitForProcess(pid, TimeSpan.FromSeconds(90));
                    ExtractZip(packagePath, appDir);
                }
                finally
                {
                    try { Directory.Delete(tempDir, true); } catch { }
                }

                RestartApp(appDir, exeName);
                return 0;
            }
            catch (Exception ex)
            {
                string logPath = Path.Combine(Path.GetTempPath(), "jisupijian_updater_error.log");
                File.WriteAllText(logPath, ex.ToString());
                return 1;
            }
        }

        private static Dictionary<string, string> ParseArgs(string[] args)
        {
            Dictionary<string, string> result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            for (int i = 0; i < args.Length; i++)
            {
                if (!args[i].StartsWith("--", StringComparison.Ordinal))
                {
                    continue;
                }

                string key = args[i].Substring(2);
                if (i + 1 >= args.Length || args[i + 1].StartsWith("--", StringComparison.Ordinal))
                {
                    result[key] = "";
                    continue;
                }

                result[key] = args[++i];
            }
            return result;
        }

        private static string Required(Dictionary<string, string> args, string key)
        {
            if (!args.ContainsKey(key) || string.IsNullOrWhiteSpace(args[key]))
            {
                throw new ArgumentException("Missing --" + key);
            }
            return args[key];
        }

        private static string Sha256File(string path)
        {
            using (SHA256 sha = SHA256.Create())
            using (FileStream stream = File.OpenRead(path))
            {
                byte[] hash = sha.ComputeHash(stream);
                return BitConverter.ToString(hash).Replace("-", "");
            }
        }

        private static void WaitForProcess(int pid, TimeSpan timeout)
        {
            if (pid <= 0)
            {
                return;
            }

            try
            {
                using (Process process = Process.GetProcessById(pid))
                {
                    process.WaitForExit((int)timeout.TotalMilliseconds);
                }
            }
            catch
            {
            }
        }

        private static void ExtractZip(string zipPath, string targetDir)
        {
            string targetRoot = Path.GetFullPath(targetDir).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            using (ZipArchive archive = ZipFile.OpenRead(zipPath))
            {
                foreach (ZipArchiveEntry entry in archive.Entries)
                {
                    string destination = Path.GetFullPath(Path.Combine(targetDir, entry.FullName));
                    if (!destination.StartsWith(targetRoot, StringComparison.OrdinalIgnoreCase))
                    {
                        throw new InvalidOperationException("Unsafe update entry: " + entry.FullName);
                    }

                    if (string.IsNullOrEmpty(entry.Name))
                    {
                        Directory.CreateDirectory(destination);
                        continue;
                    }

                    Directory.CreateDirectory(Path.GetDirectoryName(destination));
                    entry.ExtractToFile(destination, true);
                }
            }
        }

        private static void RestartApp(string appDir, string exeName)
        {
            string exePath = Path.Combine(appDir, exeName);
            if (!File.Exists(exePath) || !exePath.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
            {
                return;
            }

            ProcessStartInfo info = new ProcessStartInfo(exePath);
            info.WorkingDirectory = appDir;
            info.UseShellExecute = false;
            Process.Start(info);
        }
    }
}
