# & "C:\Program Files (x86)\MakeMKV\makemkvcon.exe" --robot --minlength=90 --messages=MakeMKVOutput.txt info disc:0
function convert-sec {
    param(
        $duration
    )
    $ts=""
    if ($duration -match [regex]"(?<Hours>\d{1}).(?<Minutes>\d{2}).(?<Seconds>\d{2})") {
        $ts = New-TimeSpan -Hours $matches.Hours -Minutes $matches.Minutes -Seconds $matches.Seconds
        return $ts.TotalSeconds
    }
    if ($duration -match [regex]"(?<Minutes>\d{2}).(?<Seconds>\d{2})") {
        $ts = New-TimeSpan -Minutes $matches.Minutes -Seconds $matches.Seconds
        return $ts.TotalSeconds
    }
    if ($duration -match [regex]"(?<Minutes>\d{1}).(?<Seconds>\d{2})") {
        $ts = New-TimeSpan -Minutes $matches.Minutes -Seconds $matches.Seconds
        return $ts.TotalSeconds
    }
}

$movie=((Select-String -Pattern "CINFO:2,0," -path .\MakeMKVOutput.txt) -replace '"', "" -split ",")[-1]

$dtrack=((Select-String -Pattern ",27,0" -path .\MakeMKVOutput.txt))
$dname=((Select-String -Pattern ",27,0" -path .\MakeMKVOutput.txt)) -replace '"', ""
$dmpl =((Select-String -Pattern ",16,0" -path .\MakeMKVOutput.txt)) -replace '"', ""
$dtime=((Select-String -Pattern  ",9,0" -path .\MakeMKVOutput.txt)) -replace '"', ""

for ($num = 0 ; $num -lt ($dname.Length) ; $num++){
    $dtrack[$num]=($dname[$num] -split ',' -split ':')[-4]
    $dname[$num]=($dname[$num] -split ',')[-1]
    $dmpl[$num]= ( $dmpl[$num] -split ',')[-1]
    $dtime[$num]=($dtime[$num] -split ',')[-1]
}

$tinfos=Import-Csv .\in_names.txt
foreach ($tinfo in $tinfos) {
    $ttitle=$tinfo.title -replace ":", ""
    $mpl=""
    for ($num = 0 ; $num -lt ($dname.Length) ; $num++) {
        $ch1=convert-sec($dtime[$num])
        $ch2=convert-sec($tinfo.length)
        if ($ch1 -and ($ch1 -eq $ch2)) {
            $mpl=$dmpl[$num]
            $track=$dtrack[$num]
            $name=$dname[$num]
        }
    }
    if ([string]::IsNullOrWhiteSpace($mpl)) {
        Write-Output "${ttitle} no mpl"
    } else {
        Write-Output "${ttitle} $mpl"
        & "C:\Program Files (x86)\MakeMKV\makemkvcon.exe" --robot --minlength=90 mkv disc:0 $track "$movie"
        move-item "$movie\$name" "$movie\$ttitle.mkv"
    }
}