<?php
error_reporting(-1);
ini_set('display_errors', 1);

require __DIR__ . '/vendor/autoload.php';

use RobRichards\WsePhp\WSSESoap;
use RobRichards\XMLSecLibs\XMLSecurityKey;

define('PRIVATE_KEY', __DIR__ .'/beta_suqia_ae.pem');
define('CERT_FILE', __DIR__ .'/Suqia.pem');
define('SERVICE_CERT', __DIR__ .'/epay5.dubai.ae.pem');

$fullPathToWsdl = dirname(__FILE__) . DIRECTORY_SEPARATOR . 'wsdl.xml';

class MySoap extends SoapClient
{

    public function __doRequest($request, $location, $saction, $version, $one_way = NULL)
    {


        $doc = new DOMDocument('1.0');
        $doc->loadXML($request);



        $objWSSE = new WSSESoap($doc);


        /* add Timestamp with no expiration timestamp */
        $objWSSE->addTimestamp();

        /* create new XMLSec Key using AES256_CBC and type is private key */
        $objKey = new XMLSecurityKey(XMLSecurityKey::RSA_SHA1, array('type' => 'private'));

        /* load the private key from file - last arg is bool if key in file (true) or is string (false) */
        $objKey->loadKey(PRIVATE_KEY, true);

        /* Sign the message - also signs appropiate WS-Security items */
        $options = array("insertBefore" => false);
        $objWSSE->signSoapDoc($objKey, $options);

        /* Add certificate (BinarySecurityToken) to the message */
        $token = $objWSSE->addBinaryToken(file_get_contents(CERT_FILE));

        /* Attach pointer to Signature */
        $objWSSE->attachTokentoSig($token);

        $objKey = new XMLSecurityKey(XMLSecurityKey::AES256_CBC);
        $objKey->generateSessionKey();

        $siteKey = new XMLSecurityKey(XMLSecurityKey::RSA_OAEP_MGF1P, array('type' => 'public'));
        $siteKey->loadKey(SERVICE_CERT, true, true);

        $options = array("KeyInfo" => array("X509SubjectKeyIdentifier" => true));
        $objWSSE->encryptSoapDoc($siteKey, $objKey, $options);

        $retVal = parent::__doRequest($objWSSE->saveXML(), $location, $saction, $version);

        $doc = new DOMDocument();
        $doc->loadXML($retVal);

        $options = array("keys" => array("private" => array("key" => PRIVATE_KEY, "isFile" => true, "isCert" => false,'passphrase'=>'Change1$$')));
        $objWSSE->decryptSoapDoc($doc, $options);

        return $doc->saveXML();
    }


}

$json_req = json_decode($argv[1], true);

$wsdl = 'https://epayment.dubai.ae/ePayHub/WSDL/PaymentAPIService.wsdl';
//$wsdl = $json_req['wsdl'];
//$sc = new MySoap($wsdl);
$sc = new MySoap($wsdl, array('proxy_host' => "100.127.10.108", 'proxy_port' => "8080"));



try {



$request_param = array(
    "spCode" => $json_req['spCode'],
    "servCode" => $json_req['servCode'],
    "responseToken" => $json_req['responseToken'],
);

$out = $sc->getResponseTokenDetails($request_param);
	//echo '<pre>';
	print_r(json_encode( $out ));
	//print_r($state);
	exit;
} catch (SoapFault $fault) {
	echo "<pre>";
    var_dump($fault);
}












