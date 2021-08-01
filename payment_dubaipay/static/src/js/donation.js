odoo.define('payment_dubaipay.donation_form', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var ajax = require('web.ajax');
var publicWidget = require('web.public.widget');

var qweb = core.qweb;
var _t = core._t;

ajax.loadXML('/payment_dubaipay/static/src/xml/dubaipay_templates.xml', qweb);


if ($.blockUI) {
    // our message needs to appear above the modal dialog
    $.blockUI.defaults.baseZ = 2147483647; //same z-index as StripeCheckout
    $.blockUI.defaults.css.border = '0';
    $.blockUI.defaults.css["background-color"] = '';
    $.blockUI.defaults.overlayCSS["opacity"] = '0.9';
}


function displayError(message) {
        //console.log('displayError', message)
        var wizard = $(qweb.render('dubaipay.error', {'msg': _t('Payment error')}));
        wizard.appendTo($('body')).modal({'keyboard': true});
        if ($.blockUI) {
            $.unblockUI();
        }
        $("#o_donation_form_pay").removeAttr('disabled');
}


publicWidget.registry.DonationForm = publicWidget.Widget.extend({
    selector: '.payment_donation',

    events: {
        'click #o_donation_form_pay': 'async donationPayNow',
        'change input[name="donation_radio"]': 'changeDonationAmount',
        'keyup #donation_other_amount': '_onKeypress',
    },

    start: function () {
        $(".donation_amount_text").hide();
        return this._super.apply(this, arguments).then(function () {
        });
    },

    _onKeypress: function (event) {
        var $target = $(event.currentTarget);
        var value = $target.val();
        this.$('.error-div').addClass("hidden_error");
        $("#donation_amount").text(value)
    },

    donationPayNow: function(ev){
         ev.preventDefault();
        // Open Checkout with further options
        
        var other_radio = this.$('input[id="donation_other_amount_radio"]').prop('checked');
        if (other_radio){
            var donation_input = this.$('input[id="donation_other_amount"]')
            var amount = $(donation_input).val();
            if(amount == '') {  
                $(donation_input).css('border', 'solid 2px #4784c1');
                this.$('.error-div').removeClass("hidden_error");
            } 
        }else{
            var amount = this.$('input[name="donation_radio"]:checked').val();
            this.$('input[id="donation_other_amount"]').css('border', '');
        }
        if (amount){
            if ($.blockUI) {
                var msg = _t("Redirecting to Payment Gateway");
                $.blockUI({
                    'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                            '    <br />' + msg +
                            '</h2>'
                });
            }
            return this._rpc({
                route: '/shop/donation/transaction',
                params: {'amount': parseInt(amount)},
            }).then(function(result) {
                if (result.message) {
                    console.log('result.message', result)
                    displayError(result.message);
                }else{
                    window.location = result
                    if ($.blockUI) {
                        $.unblockUI();
                    }
                }
            }) 
        }else{
             $("donation_other_amount").prop('required', true);
        }  
    },
    
    changeDonationAmount: function(ev){
        var other_radio = this.$('input[id="donation_other_amount_radio"]').prop('checked');
        this.$('input[id="donation_other_amount"]').css('border', '');
        this.$('.error-div').addClass("hidden_error");
        if(other_radio){
            $("#donation_other_amount").val("");
            $(".donation_amount_text").show();
            $("#donation_other_amount").prop("disabled", false);
        } else {
            var donation = this.$('input[name="donation_radio"]:checked').val();
            $("#donation_other_amount").val(donation)
            $("#donation_other_amount").prop("disabled", true);
            $(".donation_amount_text").hide();
        }
    },

});
});
