$(document).ready(function(){

    $('FoodNum').click(function(){

        $.ajax({
            url: '',
            type: 'POST',
            contentType: 'application/json',
            data: {
                button_text: $(this).text()
            },
        })

    })

})
