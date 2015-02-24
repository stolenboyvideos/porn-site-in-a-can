#!/usr/bin/perl

use strict;
use warnings;

use CGI;
use CGI::Carp 'fatalsToBrowser';

use lib '..';
use config;
use template;

use List::Util 'shuffle';

#
# figure out if the user is out of data
#

my $user = user();
my $out_of_data = 0;

#
# need movies just to show the number of movies in the outer template
#

my $movies = movies();

#
#
#

my $action = CGI::param('action') || 'view';

my $code = 'OK';
my $password = $user->cookie;
my $old_user = $user;

#
# handle login attempts
#

if( $action eq 'login' ) {

    # log in to an existing account

    my $password = CGI::param('password');
    if( ! $password or ! length($password) ) {
        print "Content-type: text/html\r\n\r\n";
        $code = 'BADPASS';
    } else {
        # the user gave a password of some sort
        ($user) = query( "select * from users where cookie = ? ", $password, );   # their password is in their cookie
        if( $user ) {
             my $cookie = CGI::cookie( -name => 'account', -value => $user->cookie, -expires => '+1y', );
             $password = $user->cookie;  # for display below
             print "Content-type: text/html\r\n";
             print "Set-Cookie: " . $cookie . "\r\n";
             print "\r\n";
             $code = 'LOGGEDIN';
        } else {
            print "Content-type: text/html\r\n\r\n";
            $code = 'NOTFOUND';
            $user = $old_user;
        }
    }

} elsif( $action eq 'register' ) {

    # create a new account

    if( $user->cookie ) {

        print "Content-type: text/plain\r\n\r\n";
        print "Already registered.\n"; # shouldn't reach here
        exit;

    }

    open my $fh, '<', $config::home . '/words' or die $!;
    my @words = shuffle( grep m/^[a-z]{4,8}$/, map { chomp; $_; } readline $fh );
    $password = join ' ', @words[1..5];

    # change this user record to match on their new cookie (same as their password) instead of ip;
    # create a new user record for that IP address without a data allocation to avoid cookie deleting attacks
    # (if we simply didn't create a new user for that IP address, one would automatically be created for anyone coming from that IP without a cookie, and it would have a default data allocation)

    query( "insert into users (ip, debug, bytes_purchased, bytes_used) values (?, ?, ?, ?)", $user->ip,  "Created when user " . $user->id . " registered", 0, 0 );

    query( "update users set ip = '', cookie = ?, debug = ? where id = ?", $password, 'Registered at ' . time, $user->id, );
    ($user) = query( "select * from users where id = ?", $user->id, );  # re-fetch the record

    my $cookie = CGI::cookie( -name => 'account', -value => $user->cookie, -expires => '+1y', );
    print "Content-type: text/html\r\n";
    print "Set-Cookie: " . $cookie . "\r\n";
    print "Location: http://$ENV{SERVER_NAME}/register.cgi\r\n";  # get rid of the CGI parameter
    print "\r\n";

    exit;


} else {

    # no action; just viewing the page

    print "Content-type: text/html\r\n\r\n";

}

my $bytes_used = $user->bytes_used;
my $bytes_purchased = $user->bytes_purchased;

if( $bytes_used > $bytes_purchased ) {
    $out_of_data = 1;
}

#
# totally money raised by the site (ha)
#

my ($total_raised) = query( "select sum(btc) as total_raised from purchases", sub { $_[0]->total_raised }, );
$total_raised = sprintf "%.2f\n", $total_raised;

#
# show registratoin
#

my $clip = <<'EOF';

<!-- style -->

<br/>

<style type="text/css">

table {
    alight: right;
}

table th {
    font-weight: normal;
}

table td {
    background: #f4f4f4;
    padding: 10px;
}

</style>

<div>

    <div style="float: left;" class="rounded">
        <img class="pic" src="register1.png" width="259" height="203" alt="" /><br />
        <img  class="pic"src="register2.png" width="259" height="203" alt="" />
    </div>

    <!-- conditionally shown divs in the middle of the page -->
    
    <div class="rounded reginfo">
        <b>Account Status</b><br/><br/>
        <table width="100%"><tr><th valign="top">
            <table align="left">
                <tr><th>Purchased</th><th>&nbsp;</th><th>Used</th></tr>
                <tr><td>:gigs_purchased: GB</td><th>&nbsp;</th><td>:gigs_used: GB</td></tr>
            </table>
            <br>
        </th><th align="center" valign="top">
            <img src="cake.jpg" width="103" height="122">
        </th><th align="left" valign="top">
            We're a better porn site, with no ads, no fake videos that don't exist, and no auto-renew.<br/><br/>
            :total_raised: BTC from memberships help offset our annual 0.8877 BTC hosting costs.<br/>
        </th></table>
    </div>
    
    <div id="outofdata" class="rounded reginfo hidden" style="background: red;">
        You've used up your data allocation.
    </div>
    
    <div id="badpass" class="rounded reginfo hidden">
        Sorry, bad password.  Please try again.
    </div>
    
    <div id="loggedin" class="rounded reginfo hidden">
        You are now logged in.
    </div>
    
    <div id="login_form" class="rounded reginfo hidden">
    
        <b>Existing Users</b><br/><br/>
        <form method="post">
        <input type="hidden" name="action" value="login">
        <input type="text" name="password" placeholder="enter your passphrase here"><input type="submit" value="Login" style="width: 55px;">
        </form>
    </div>

    <div id="register_form" class="rounded reginfo hidden">
        <b>Register</b><br/><br/>
        Registration is just one click.  No information required.  
        Registering on this site sets a browser cookie with a one year expiration, and assigns you a randomly generated passphrase
        to use to log in to the site from other computers or if your cookie is cleared or lost.
        After registration, you'll be able to fund your account.<br/><br/>
        Pay only for the video you watch.  <b>1 GB</b> costs <b>0.003 BTC</b>.<br/><br/>
        <a href="?action=register"><!-- Or click here to register. --><img src="register.gif"/></a><br/>
    </div>
    
    <div id="logged_in" class="rounded reginfo hidden">
        <b>Welcome</b>, anonymous registered user!<br/><br/>
        Your <b>randomly generated passphrase</b> is ":password:".<br/><br/>
        Please write that down.  You'll need it to log in to the site from other computers or if your cookie is deleted.<br/>
    </div>

    <div id="add_funds_error" class="rounded reginfo hidden" style="background: red;">
    </div>
    
    <div id="add_funds" class="rounded reginfo hidden">
        Add funds to your account:
        <a href="#" onclick="add_funds(); return false;">Click here.</a>
        <a href="#" onclick="add_funds(); return false;"><img src="bitcoin.png" width="128" height="128"></a>
        <br/>
    </div>
    
    <div id="add_funds_dialog" class="rounded reginfo hidden">
        Generating a Bitcoin payment address...<br/><br/>
        <div id="loaderImage"></div>
    </div>

    <!-- end conditionally shown divs -->
    
</div>


<script type="text/javascript">

$(document).ready(function() {

    if( :logged_in: ) {
        $('#logged_in').show();
        $('#add_funds').show();
    } else {
        $('#login_form').show();
        $('#register_form').show();
    }

    if( :out_of_data: ) {
        $('#outofdata').show();
    }

    switch( ':code:' ) {
        case 'NOTFOUND':
        case 'BADPASS':
            $('#badpass').show();
        break;
        case 'LOGGEDIN':
            $('#loggedin').show();
        break;
    }

});

function add_funds() {

    // the user clicked the add funds button

    // hide the dialog with the link to add funds and show the dialog that will display the bitcoin address to send to

    // $('#add_funds').hide();
    $('#add_funds').animate({
        height:  'toggle',
    }, 'slow');

    // $('#add_funds_dialog').show();
    $('#add_funds_dialog').animate({
        height:  'toggle',
    }, 'slow');

    // animate while a bitcoin address is fetched

    new imageLoader(cImageSrc, 'startAnimation()');

    // fetch a destination bitcoin address for the user to send payment to and display the address and instructions in the UI

    $.ajax({
        url: "/payment.cgi",
    }).done(function( res ) {
        if( res.error ) {
            payment_error( res.error );
        } else {
            $('#add_funds_dialog').html( 
                "Use your BitCoin wallet or trading account to send 0.003 BTC per gigabyte of video to purchase to this address: <b><a href='bitcoin:" + res.input_address + "'>" + res.input_address +"</a></b><br/><br/>" +
                '<a href="http://www.wolframalpha.com/input/?i=' + res.input_address + '+qr+code" target="_blank">Click here for a QR code</a><br/>'
            );
        }
    }).fail(function( jqXHR, textStatus ) {
        payment_error( textStatus );
    });

    // poll to see if payment has been recieved
    // reload the page to show updated balance when it has

    var payment_poll_timer;
    var poll_function;
    poll_function = function () {
        $.ajax({
            url: "/payment.cgi?action=check",
        }).done(function( res ) {
            if( res.paid ) {
                clearTimeout(payment_poll_timer);
                location.reload();
            } else {
                payment_poll_timer = setTimeout(poll_function, 2 * 1000);
            }
            // TODO detect error status
        });
    };
    payment_poll_timer = setTimeout(poll_function, 2 * 1000);

}

function payment_error(text) {
    $('#add_funds').show();
    $('#add_funds_error').html("Payment error: " + error + "<br/>").show();
    $('#add_funds_dialog').hide();
}
 
</script>


EOF

#
#
#

my $content = template(
    $clip, {
        logged_in => ($user->cookie ? 1 : 0),
        code => $code,
        gigs_used => sprintf( "%.2f", $bytes_used / 1024 / 1024 / 1024 ),
        gigs_purchased => sprintf( "%.2f", $bytes_purchased / 1024 / 1024 / 1024 ),
        out_of_data => $out_of_data,
        password => $password,
        total_raised => $total_raised,
        # promo_movies1 => some_movies( $movies, 2 ), # just using static images to avoid movie play clutter
        # promo_movies2 => some_movies( $movies, 2 ),
    },
);

print template( undef, {
    content => $content,
    num_videos => $movies->num_rows,
    logged_in => ($user->cookie ? 1 : 0),
} );


