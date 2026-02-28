cd /Users/supremeleader/Documents/fsu_graphics_bot

cat > executors/ps_export_layer_manifest.scpt <<'APPLESCRIPT'
on run argv
	if (count of argv) < 1 then
		error "Usage: ps_export_layer_manifest.scpt <psd_path>"
	end if
	
	set psdPath to item 1 of argv
	set psdJs to my esc(psdPath)
	
	set js to ""
	set js to js & "var psd = new File('" & psdJs & "');" & return
	set js to js & "if (!psd.exists) throw new Error('PSD missing');" & return
	set js to js & "var doc = null;" & return
	set js to js & "doc = app.open(psd);" & return
	set js to js & "var ok = false;" & return
	set js to js & "var errMsg = null;" & return
	set js to js & "try {" & return
	
	-- recursive layer walk
	set js to js & "function walk(parent, out) {" & return
	set js to js & "  for (var i = 0; i < parent.layers.length; i++) {" & return
	set js to js & "    var l = parent.layers[i];" & return
	set js to js & "    out.push(l);" & return
	set js to js & "    if (l.typename === 'LayerSet') walk(l, out);" & return
	set js to js & "  }" & return
	set js to js & "}" & return
	
	set js to js & "function jsonEscape(s) {" & return
	set js to js & "  return String(s).replace(/\\\\/g, '\\\\\\\\').replace(/\"/g, '\\\\\"');" & return
	set js to js & "}" & return
	
	set js to js & "function jsonArray(arr) {" & return
	set js to js & "  var out = '[';" & return
	set js to js & "  for (var i = 0; i < arr.length; i++) {" & return
	set js to js & "    if (i) out += ', ';" & return
	set js to js & "    out += '\"' + jsonEscape(arr[i]) + '\"';" & return
	set js to js & "  }" & return
	set js to js & "  out += ']';" & return
	set js to js & "  return out;" & return
	set js to js & "}" & return
	
	set js to js & "var all = [];" & return
	set js to js & "walk(doc, all);" & return
	set js to js & "var names = [];" & return
	set js to js & "var smart = [];" & return
	set js to js & "for (var i = 0; i < all.length; i++) {" & return
	set js to js & "  var l = all[i];" & return
	set js to js & "  names.push(l.name);" & return
	set js to js & "  try { if (l.kind === LayerKind.SMARTOBJECT) smart.push(l.name); } catch (e) {}" & return
	set js to js & "}" & return
	
	-- build output text FIRST (no JSON.stringify usage)
	set js to js & "var text = '{\\n' +" & return
	set js to js & "  '  \"schema_version\": 1,\\n' +" & return
	set js to js & "  '  \"smart_object_layers\": ' + jsonArray(smart) + ',\\n' +" & return
	set js to js & "  '  \"layers\": ' + jsonArray(names) + '\\n' +" & return
	set js to js & "  '}\\n';" & return
	
	-- output path: <psd>.layer_manifest.json (same folder)
	set js to js & "var outPath = psd.fullName.replace(/\\.psd$/i, '.layer_manifest.json');" & return
	set js to js & "var outFile = new File(outPath);" & return
	set js to js & "outFile.open('w');" & return
	set js to js & "outFile.write(text);" & return
	set js to js & "outFile.close();" & return
	set js to js & "ok = true;" & return
	
	set js to js & "} catch (e) {" & return
	set js to js & "  errMsg = (e && e.message) ? e.message : String(e);" & return
	set js to js & "} finally {" & return
	set js to js & "  try { if (doc) doc.close(SaveOptions.DONOTSAVECHANGES); } catch (e2) {}" & return
	set js to js & "}" & return
	set js to js & "if (errMsg) throw new Error(errMsg);" & return
	set js to js & "if (ok) 'OK';" & return
	
	tell application "Adobe Photoshop 2026"
		activate
		set resultText to do javascript js
	end tell
	
	return resultText
end run

on esc(s)
	set AppleScript's text item delimiters to "'"
	set parts to text items of s
	set AppleScript's text item delimiters to "\\'"
	set outText to parts as text
	set AppleScript's text item delimiters to ""
	return outText
end esc
APPLESCRIPT