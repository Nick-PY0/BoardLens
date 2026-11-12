using System;
using System.IO;
using System.IO.Compression;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Threading.Tasks;
using System.Windows.Forms;

[assembly: System.Runtime.Versioning.TargetFramework(".NETFramework,Version=v4.8")]

static class BoardLensLauncher {
    const string Hash="@PAYLOAD_SHA@";
    static string Root=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"BoardLens","native");
    static string Package=Path.Combine(Root,"packages",Hash.Substring(0,20));
    static string Smoke;
    [STAThread] static int Main(string[] args) {
        AppContext.SetSwitch("Switch.System.IO.UseLegacyPathHandling",false);
        AppContext.SetSwitch("Switch.System.IO.BlockLongPaths",false);
        Application.EnableVisualStyles();
        for(int i=0;i+1<args.Length;i++)if(args[i]=="--self-test")Smoke=Path.GetFullPath(args[i+1]);
        try {
            if(!File.Exists(Path.Combine(Package,".ready"))) {
                Form splash=new Form {Text="BoardLens",Width=430,Height=155,StartPosition=FormStartPosition.CenterScreen,FormBorderStyle=FormBorderStyle.FixedDialog,MaximizeBox=false,MinimizeBox=false};
                splash.Controls.Add(new Label {Text="Preparing BoardLens…",Left=24,Top=22,Width=360,Height=28,Font=new System.Drawing.Font("Segoe UI",12)});
                splash.Controls.Add(new ProgressBar {Left=24,Top=64,Width=365,Style=ProgressBarStyle.Marquee});
                Exception failed=null;splash.Shown+=(s,e)=>Task.Run(()=>{try{Prepare();}catch(Exception error){failed=error;}splash.BeginInvoke(new Action(()=>splash.Close()));});
                Application.Run(splash);if(failed!=null)throw failed;
            }
            return Launch();
        }catch(Exception error){if(Smoke!=null){Directory.CreateDirectory(Path.GetDirectoryName(Smoke));File.WriteAllText(Smoke,"{\"launcher_error\":\""+error.Message.Replace("\\","/").Replace("\"","'")+"\"}");}else MessageBox.Show(error.Message,"BoardLens could not start",MessageBoxButtons.OK,MessageBoxIcon.Error);return 1;}
    }
    static void Prepare(){
        string payload=Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"Resources","payload.zip");
        using(var stream=File.OpenRead(payload))using(var sha=SHA256.Create()){string actual=BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();if(actual!=Hash)throw new Exception("The app package checksum did not match. Download the complete Windows ZIP again.");}
        Directory.CreateDirectory(Path.GetDirectoryName(Package));string stage=Path.Combine(Path.GetDirectoryName(Package),".stage-"+Guid.NewGuid().ToString("N").Substring(0,12));Directory.CreateDirectory(stage);
        try{using(var zip=ZipFile.OpenRead(payload)){long size=0;foreach(var entry in zip.Entries){size+=entry.Length;if(size>4L*1024*1024*1024)throw new Exception("Unexpected package size.");string destination=Path.GetFullPath(Path.Combine(stage,entry.FullName));if(!destination.StartsWith(stage+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new Exception("Unsafe package entry.");if(entry.FullName.EndsWith("/")){Directory.CreateDirectory(destination);continue;}Directory.CreateDirectory(Path.GetDirectoryName(destination));entry.ExtractToFile(destination);}}
            File.WriteAllText(Path.Combine(stage,".ready"),"ready");if(Directory.Exists(Package)){if(File.Exists(Path.Combine(Package,".ready")))Directory.Delete(stage,true);else throw new Exception("An incomplete package exists. Close BoardLens and retry.");}else Directory.Move(stage,Package);
        }catch{if(Directory.Exists(stage))Directory.Delete(stage,true);throw;}
    }
    static int Launch(){
        string logs=Path.Combine(Root,"logs");Directory.CreateDirectory(logs);
        ProcessStartInfo info=new ProcessStartInfo(Path.Combine(Package,"runtime","pythonw.exe"),"\""+Path.Combine(Package,"start.py")+"\"");info.UseShellExecute=false;info.CreateNoWindow=true;info.WorkingDirectory=Package;info.RedirectStandardOutput=true;info.RedirectStandardError=true;
        foreach(string key in new[]{"PYTHONHOME","PYTHONPATH","VIRTUAL_ENV","__PYVENV_LAUNCHER__"})info.EnvironmentVariables.Remove(key);
        info.EnvironmentVariables["BOARDLENS_NATIVE_DATA"]=Root;
        info.EnvironmentVariables["BOARDLENS_NATIVE_LAUNCHER"]=Application.ExecutablePath;
        if(Smoke!=null){info.EnvironmentVariables["BOARDLENS_NATIVE_SMOKE"]=Smoke;info.EnvironmentVariables["BOARDLENS_DATA_DIR"]=Path.Combine(Path.GetDirectoryName(Smoke),"smoke-data");info.EnvironmentVariables["BOARDLENS_TEST_MODE"]="1";info.EnvironmentVariables["PYNPUT_BACKEND"]="dummy";info.EnvironmentVariables["QT_QPA_PLATFORM"]="offscreen";}
        var process=new Process {StartInfo=info};object gate=new object();string log=Path.Combine(logs,"latest.log");DataReceivedEventHandler received=(s,e)=>{if(e.Data!=null)lock(gate)File.AppendAllText(log,e.Data+Environment.NewLine);};process.OutputDataReceived+=received;process.ErrorDataReceived+=received;process.Start();process.BeginOutputReadLine();process.BeginErrorReadLine();
        if(Smoke!=null){for(int i=0;i<1800;i++){if(File.Exists(Smoke))return 0;System.Threading.Thread.Sleep(100);}throw new Exception("The application self-test timed out; see "+log);}
        // The windowless launcher stays with its GUI child to retain redirected logs.
        process.WaitForExit();return process.ExitCode;
    }
}
