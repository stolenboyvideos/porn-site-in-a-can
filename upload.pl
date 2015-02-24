#!/usr/bin/perl

use strict;
use warnings;

use Getopt::Long;
use Image::Info;
use Movie::Info;

use config;

use template;
use query;

use Data::Dumper;
use MD5;

GetOptions(
    "movie=s"   => \my $movie_fn,
    "thumb=s"   => \my $thumb_fn,
    "runtime=s"   => \my $runtime,
    "convert"   => \my $convert,
);

$movie_fn ||= $ARGV[0] if @ARGV == 1;

die "specify --movie" if ! $movie_fn;

die "movie file not found" if $movie_fn and ! -f $movie_fn;
die "thumb file not found" if $thumb_fn and ! -f $thumb_fn;

#
# if flv, re-package the stream into a temporary file
#

my $file_info = `file "$movie_fn"`;
if( ( $convert or $movie_fn =~ m{\.flv$} ) and $file_info !~ m/MPEG v4/ ) {

    # eg:  /dir/dir/purple_singlet_dick_up_3727272_flv.mp4: ISO Media, MPEG v4 system, version 2

    (my $movie_base_fn = $movie_fn) =~ s{.*/}{};  # temp; file extension will change
    $movie_base_fn =~ s{\.flv}{\.mp4} or die;

    if( $convert ) {
        system qq{ ffmpeg -i "$movie_fn" -strict -2 "/tmp/$movie_base_fn" } and die;                  #  have to do something like that if the encoding isn't compatible
    } else {
        system qq{ ffmpeg -i "$movie_fn" -vcodec copy -acodec copy "/tmp/$movie_base_fn" } and die; 
    }

    $movie_fn = "/tmp/$movie_base_fn";  # moved to /tmp and extention changed
}

#
# compute $movie_base_fn and $thumb_fn
#

(my $movie_base_fn = $movie_fn) =~ s{.*/}{};
if( ! $thumb_fn ) {
    $thumb_fn = $movie_fn;  $thumb_fn =~ s{\.mp4$}{\.jpg} or die "couldn't change $movie_fn to end in .jpg";
}


#
# qtfaststart
#

system '/usr/local/bin/qtfaststart', $movie_fn; # XXX only for mp4

#
# checksum the movie for duplicate control and thumbnail naming
#

my $md5sum = do {
    my $md5 = MD5->new;
    $md5->reset();
    open my $fh, '<', $movie_fn or die "$movie_fn: $!";
    $md5->addfile($fh);
    $md5->hexdigest();
};

#
# check for duplicates
#

my ($dup) = query( "select * from movies where md5 = ? ", $md5sum );
die 'this movie is a duplicate of: ' . $dup->mp4 if $dup;

#
# copy the file up
#

system 'cp', '-f', $movie_fn, $config::home . '/video/' and die $?;

#
# thumbnail 
#

my $thumb_out_fn = $config::home . "/public_html/thumbs/$md5sum.jpg";

if( -f $thumb_fn ) {

    # copy the thumbnail directly if possible or scale it if needed

    my $image_inf = Image::Info::image_info( $thumb_fn ) or die;
    (my $w, my $h) = Image::Info::dim( $image_inf );   # should be 310, 235
    if( $w == 310 and $h == 235 ) {
        system 'cp', '-f', $thumb_fn, "/mnt/site/public_html/thumbs/$md5sum.jpg" and die $?;
    } else {
        # could use pnmcut instead
        system "djpeg '$thumb_fn' | pnmscale -xysize 310 235 | cjpeg > '$thumb_out_fn'" and die $?;
    }

} else {

    # generate and rescale an image thumbnail

    # system "ffmpegthumbnailer -s 310 -i "$movie_fn"  -o "/mnt/site/public_html/thumbs/$md5sum.jpg"' and die $?; # simple version with no rescaling

    # system "ffmpegthumbnailer -t '30%' -s 310 -i '$movie_fn'  -o '/tmp/tmp.jpg'" and die $?;    # rescale using a jpg as a temp file
    # system "djpeg '/tmp/tmp.jpg' | pnmscale -xysize 310 235 | cjpeg > '$thumb_out_fn' " and die $?;

    system "ffmpegthumbnailer -t '20%' -s 310 -i '$movie_fn'  -o '/tmp/tmp.png'" and die $?;      # rescale using a png as a temp file
    system "pngtopnm '/tmp/tmp.png' | pnmscale -xysize 310 235 | cjpeg > '$thumb_out_fn' " and die $?;
    warn "generated thumbnail $thumb_out_fn";

}

#
# runlength
#

if( ! $runtime ) {
    my $mi = Movie::Info->new;
    my %info = $mi->info($movie_fn) or die;
    $runtime = $info{length} or die;
    $runtime =~ s{\.\d\d$}{} or die "couldn't parse length $runtime";
    my $minutes = int( $runtime / 60 );
    my $seconds = $runtime % 60;
    $runtime = sprintf "%d:%02d", $minutes, $seconds;
    warn "computed runtime: $runtime";
}

#
# insert it
#

query( "insert into movies (mp4, jpg, runtime, md5) values (?, ?, ?, ?)", $movie_base_fn, "$md5sum.jpg", $runtime, $md5sum, );



