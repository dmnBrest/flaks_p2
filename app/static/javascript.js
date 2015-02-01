jQuery(function(){

	var csrftoken = $('meta[name=csrf-token]').attr('content');
	jQuery.ajaxSetup({
		beforeSend: function(xhr, settings) {
			if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
				xhr.setRequestHeader("X-CSRFToken", csrftoken)
			}
		}
	});

	jQuery('time').each(function(){
		var d = jQuery(this).attr('datetime');
		jQuery(this).text(moment(d).format("LL"));
	});
});

function animateScrollToHash(hash, speed, callback) {
	$('html, body').animate({
		scrollTop: $(hash).offset().top
	}, speed, callback());
}

function picsGalleryPopup(type) {
	var w = 1000;
	var h = 800;
	var left = (screen.width/2)-(w/2);
	var top = (screen.height/2)-(h/2);
	var win = window.open('/uploads?inline=true&type='+type, 'PicsGallery', 'toolbar=no, location=no, directories=no, status=no, menubar=no, scrollbars=no, resizable=no, copyhistory=no, width='+w+', height='+h+', top='+top+', left='+left);
	win.focus();
	return win;
}
