function picsGalleryPopup(type) {
	var w = 1000;
	var h = 800;
	var left = (screen.width/2)-(w/2);
	var top = (screen.height/2)-(h/2);
	var w = window.open('/pictures?inline=true&type='+type, 'PicsGallery', 'toolbar=no, location=no, directories=no, status=no, menubar=no, scrollbars=no, resizable=no, copyhistory=no, width='+w+', height='+h+', top='+top+', left='+left);
	w.focus();
	return w;
}