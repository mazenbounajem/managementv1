$path = 'C:\Users\USER\AppData\Roaming\Code\User\settings.json'
if (Test-Path $path) {
    $content = Get-Content $path -Raw
    if ($content) {
        $settings = $content | ConvertFrom-Json
    } else {
        $settings = @{}
    }
} else {
    $settings = @{}
}
$settings | Add-Member -MemberType NoteProperty -Name 'window.openFilesInNewWindow' -Value 'on' -Force
$settings | ConvertTo-Json -Depth 10 | Set-Content $path
