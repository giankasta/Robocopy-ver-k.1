param(
    [Parameter(Mandatory = $true)]
    [string]$Source,
    [Parameter(Mandatory = $true)]
    [string]$Destination
)

$ErrorActionPreference = "Stop"

function Find-ShellFolderItem($ParentFolder, [string]$Name) {
    $items = $ParentFolder.Items()
    for ($index = 0; $index -lt $items.Count; $index++) {
        $item = $items.Item($index)
        if ([string]::Equals($item.Name, $Name, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $item
        }
    }
    return $null
}

function Copy-MtpFolder($SourceFolder, [string]$DestinationPath, [string]$RelativePath) {
    $items = $SourceFolder.Items()
    for ($index = 0; $index -lt $items.Count; $index++) {
        $item = $items.Item($index)
        $targetPath = Join-Path $DestinationPath $item.Name
        $relativeTarget = if ($RelativePath) { Join-Path $RelativePath $item.Name } else { $item.Name }

        if ($item.IsFolder) {
            $null = New-Item -ItemType Directory -Path $targetPath -Force
            Copy-MtpFolder $item.GetFolder() $targetPath $relativeTarget
            continue
        }

        $expectedSize = [int64]$item.Size
        $expectedDate = $item.ModifyDate
        $alreadyCopied = $false
        if (Test-Path -LiteralPath $targetPath -PathType Leaf) {
            $existing = Get-Item -LiteralPath $targetPath
            $dateMatches = $true
            if ($expectedDate -is [datetime]) {
                $dateMatches = [math]::Abs(($existing.LastWriteTime - $expectedDate).TotalSeconds) -le 3
            }
            $alreadyCopied = ($existing.Length -eq $expectedSize) -and $dateMatches
        }

        if ($alreadyCopied) {
            Write-Output ("Gia' presente: " + $relativeTarget)
            continue
        }

        $destinationFolder = $script:shell.Namespace($DestinationPath)
        if ($null -eq $destinationFolder) {
            throw "Impossibile aprire la destinazione: $DestinationPath"
        }
        Write-Output ("Copia: " + $relativeTarget)
        $destinationFolder.CopyHere($item, 20)

        $deadline = [datetime]::UtcNow.AddMinutes(30)
        $stableCount = 0
        $lastLength = -1
        $lastDate = [datetime]::MinValue
        while ([datetime]::UtcNow -lt $deadline) {
            if (Test-Path -LiteralPath $targetPath -PathType Leaf) {
                $copied = Get-Item -LiteralPath $targetPath
                $dateMatches = $true
                if ($expectedDate -is [datetime]) {
                    $dateMatches = [math]::Abs(($copied.LastWriteTime - $expectedDate).TotalSeconds) -le 3
                }
                if ($copied.Length -eq $expectedSize -and $dateMatches) {
                    if ($copied.Length -eq $lastLength -and $copied.LastWriteTime -eq $lastDate) {
                        $stableCount++
                    }
                    else {
                        $stableCount = 0
                    }
                    if ($stableCount -ge 3) {
                        break
                    }
                    $lastLength = $copied.Length
                    $lastDate = $copied.LastWriteTime
                }
            }
            Start-Sleep -Milliseconds 500
        }

        if ($stableCount -lt 3) {
            throw "Trasferimento non verificato o scaduto per: $relativeTarget"
        }
        Write-Output ("Completato: " + $relativeTarget)
    }
}

try {
    $shell = New-Object -ComObject Shell.Application
    $script:shell = $shell
    $segments = @($Source.Trim().Trim('\').Split('\') | Where-Object { $_ })
    if ($segments.Count -gt 0 -and $segments[0] -in @("Questo PC", "This PC", "Computer")) {
        $segments = @($segments | Select-Object -Skip 1)
    }
    if ($segments.Count -eq 0) {
        throw "Percorso iPhone vuoto. Esempio: Questo PC\Apple iPhone\Internal Storage"
    }

    $currentFolder = $shell.Namespace(17)
    foreach ($segment in $segments) {
        $item = Find-ShellFolderItem $currentFolder $segment
        if ($null -eq $item -or -not $item.IsFolder) {
            throw "Elemento non trovato in 'Questo PC': $segment. Verifica che l'iPhone sia sbloccato e autorizzato."
        }
        $currentFolder = $item.GetFolder()
    }

    $null = New-Item -ItemType Directory -Path $Destination -Force
    Copy-MtpFolder $currentFolder $Destination ""
    Write-Output "Trasferimento iPhone completato."
    exit 0
}
catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}